"""Local media checks and source provenance for explicitly requested recovery."""
from concurrent.futures import ThreadPoolExecutor
from collections import OrderedDict
from pathlib import Path
import hashlib
import json
import math
import sqlite3
import threading
import uuid

from src.content_packages import scheduled_video_path
from src.media_validation import probe_video
from multi_pc.json_io import replace_with_retry

_LOCK = threading.RLock()
_CACHE = {}
_DIGEST_CACHE = OrderedDict()


def media_key(output_dir, path):
    return Path(path).resolve().relative_to(Path(output_dir).resolve()).as_posix()


def checked_video(output_dir, filename, *, refresh=False):
    path = scheduled_video_path(output_dir, filename)
    from src.media_quality_gate import require_publishable
    require_publishable(path)
    if path.suffix.lower() != ".mp4" or path.is_symlink():
        raise ValueError("Chọn file MP4 trong kho của ứng dụng.")
    stat = path.stat()
    key = str(path)
    signature = (stat.st_size, stat.st_mtime_ns)
    with _LOCK:
        cached = _CACHE.get(key)
    if not refresh and cached and cached[0] == signature:
        return path, dict(cached[1])
    info = probe_video(path)
    with _LOCK:
        _CACHE[key] = (signature, dict(info))
    return path, info


def file_digest(path):
    before = Path(path).stat()
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    after = Path(path).stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError("Video đang thay đổi; chờ render hoàn tất rồi thử lại.")
    return digest.hexdigest()


def verify_recovery_digest(post, path):
    expected = str(post.get("replacement_video_sha256") or "")
    if expected and file_digest(path) != expected:
        raise ValueError("MP4 thay thế đã thay đổi sau khi duyệt; kiểm tra lại clip và Content trước khi đăng.")


def inventory_digest(path):
    """Cache browsing hashes only; commit and upload still hash the actual bytes."""
    path = Path(path)
    stat = path.stat()
    signature = (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
    key = str(path.resolve())
    with _LOCK:
        cached = _DIGEST_CACHE.get(key)
        if cached and cached[0] == signature:
            _DIGEST_CACHE.move_to_end(key)
            return cached[1]
    digest = file_digest(path)
    after = path.stat()
    if signature != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        raise ValueError("Video đã thay đổi trong lúc kiểm tra kho; tải lại danh sách.")
    with _LOCK:
        _DIGEST_CACHE[key] = (signature, digest)
        while len(_DIGEST_CACHE) > 512:
            _DIGEST_CACHE.popitem(last=False)
    return digest


def read_json(path, default):
    if not Path(path).exists():
        return default
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name("." + path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        replace_with_retry(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def reusable_content(filename, sha, metadata, packages):
    """Find ready Content for these bytes and this original source only."""
    from src.content_packages import _reusable, _clip_keys
    from src.publisher.website_publisher import extract_youtube_video_id
    youtube_id = extract_youtube_video_id(metadata.get("youtube_id")) or extract_youtube_video_id(metadata.get("youtube_url"))
    basename = Path(str(filename)).name.casefold()
    keys = _clip_keys(filename)
    for item in reversed(packages):
        same_hash = item.get("source_sha256") == sha
        if not same_hash and Path(str(item.get("clip_filename") or "")).name.casefold() != basename:
            continue
        same_file = bool(keys & _clip_keys(item.get("clip_filename")))
        if not same_hash and not same_file:
            continue
        if item.get("source_sha256") and item["source_sha256"] != sha:
            continue
        source_id = (extract_youtube_video_id(item.get("youtube_id")) or extract_youtube_video_id(item.get("video_url")) or
                     extract_youtube_video_id(item.get("website_video_url")))
        if not youtube_id or source_id != youtube_id or not _reusable(item, needs_article=True):
            continue
        url = str(item.get("article_url") or "")
        if (item.get("embed_status") == "ready" and item.get("website_video_status") in (None, "", "youtube_embed_verified")
                and str((item.get("result") or {}).get("first_comment") or "").count(url) == 1):
            return item
    return None


def inventory(output_dir, post, posts, *, offset=0, limit=12):
    """Check a small page in parallel; cached checks expire when bytes change."""
    from src.publisher.website_publisher import get_clip_metadata, extract_youtube_video_id
    root = Path(output_dir).resolve()
    from src.content_packages import list_packages
    packages = list_packages()
    # This is only a sorting hint. reusable_content validates the exact selected
    # bytes and language below. Running language detection for the entire queue
    # before returning twelve clips can block the picker for several minutes.
    prepared_names = {
        Path(str(item.get("clip_filename") or "")).name
        for item in packages
        if item.get("status") == "ready" and item.get("website_status") == "ready"
        and item.get("article_url") and (item.get("result") or {}).get("caption")
    }
    held_names = {
        str(item.get("media_file") or item.get("clip_filename") or "").replace("\\", "/").rsplit("/", 1)[-1]
        for item in posts
        if item.get("id") != post.get("id")
        and (item.get("page_id") or item.get("status") in
             ("published", "publishing", "meta_handoff", "meta_scheduled", "processing"))
        and item.get("status") not in ("superseded", "cancelled")
    }
    names = sorted((p for p in root.glob("*.mp4") if not p.is_symlink() and ".rendering." not in p.name),
                   key=lambda p: (-p.stat().st_mtime_ns, p.name))
    current = str(post.get("media_file") or post.get("clip_filename") or "")
    # The rejected file itself is the last automatic choice. Prefer unused
    # clips with a ready Website/comment to avoid a new LLM/CMS/render cycle.
    names.sort(key=lambda p: (p.name in held_names, p.name == current, p.name not in prepared_names))
    selected = names[offset:offset + limit]
    claims = {}
    ledger = root.parent / "data" / "output_ledger.sqlite3"
    if ledger.is_file():
        with sqlite3.connect(ledger.as_uri() + "?mode=ro", uri=True) as db:
            claims = {row[0]: {"post_id": row[1], "assigned": row[2], "published": row[3]}
                      for row in db.execute("SELECT sha256,post_id,assigned,published FROM sources")}

    def check(path):
        row = {"filename": path.name, "title": path.stem, "valid": False, "reason": ""}
        try:
            held_name = next((p for p in posts if p.get("id") != post.get("id") and
                str(p.get("media_file") or p.get("clip_filename") or "").replace("\\", "/").rsplit("/", 1)[-1] == path.name and
                (p.get("page_id") or p.get("status") in ("published", "publishing", "meta_handoff", "meta_scheduled", "processing")) and
                p.get("status") not in ("superseded", "cancelled")), None)
            if held_name:
                row["reason"] = "Đã được giữ cho bài/Page: " + str(held_name.get("page_name") or held_name.get("page_id") or held_name["id"])
                return row
            _, info = checked_video(root, path.name)
            sha = inventory_digest(path)
            meta = get_clip_metadata(path.name)
            row.update(info, title=meta.get("video_title") or path.stem,
                       source_url=meta.get("youtube_url") or "", same_file=path.name == current)
            held = next((p for p in posts if p.get("id") != post.get("id") and
                         (str(p.get("media_file") or p.get("clip_filename") or "") == path.name or p.get("source_sha256") == sha) and
                         (p.get("page_id") or p.get("status") in ("published", "publishing", "meta_handoff", "meta_scheduled", "processing")) and
                         p.get("status") not in ("superseded", "cancelled")), None)
            if held:
                row["reason"] = "Đã được giữ cho bài/Page: " + str(held.get("page_name") or held.get("page_id") or held["id"])
            elif sha in claims and (claims[sha]["published"] or (claims[sha]["assigned"] and claims[sha]["post_id"] != post["id"])):
                row["reason"] = "Video đã được phân bổ hoặc đã đăng; chọn clip chưa được giữ cho bài khác."
            elif not (extract_youtube_video_id(meta.get("youtube_url")) or extract_youtube_video_id(meta.get("youtube_id"))):
                row["reason"] = "Thiếu link video gốc để tạo Website có embed; chọn clip có nguồn."
            else:
                row["valid"] = True
                ready = reusable_content(path.name, sha, meta, packages)
                if ready:
                    row.update(ready_content=True, article_url=ready["article_url"], content_package_id=ready["id"])
                row["same_source"] = bool(extract_youtube_video_id(post.get("youtube_id") or post.get("video_url")) ==
                                          (extract_youtube_video_id(meta.get("youtube_url")) or extract_youtube_video_id(meta.get("youtube_id"))))
        except (ValueError, OSError):
            row["reason"] = "MP4 thiếu hoặc hỏng, đang render, hoặc chưa kiểm tra được bằng FFprobe."
        return row

    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(check, selected))
    rows.sort(key=lambda row: (not row["valid"], row.get("same_file", False), not row.get("ready_content"), not row.get("same_source")))
    return {"candidates": rows, "total": len(names), "offset": offset,
            "next_offset": offset + limit if offset + limit < len(names) else None}


def recovery_interval(metadata, duration):
    """Retain valid boundaries, or explicitly record a reselected interval."""
    try:
        start = float(metadata.get("clip_start"))
        end = float(metadata.get("clip_end"))
    except (ValueError, TypeError):
        start, end = 0.0, min(55.0, duration)
    original = (start, end)
    wanted = min(60.0, max(5.0, end - start)) if math.isfinite(end - start) else 55.0
    wanted = min(wanted, duration)
    if not math.isfinite(start) or not math.isfinite(end) or start < 0 or start >= duration or end <= start:
        try:
            position = min(2, max(0, int(metadata.get("clip_index") or 1) - 1)) / 2
        except (ValueError, TypeError):
            position = 0
        start = max(0.0, duration - wanted) * position
        end = start + wanted
    else:
        end = min(end, duration)
    if end - start <= 0:
        raise ValueError("Video gốc không có đoạn cắt hợp lệ.")
    return start, end, original != (start, end)


def save_recovery_source(root, filename, metadata, sha):
    path = Path(root) / "data" / "video_recovery_sources.json"
    with _LOCK:
        rows = read_json(path, {})
        rows[filename] = {"sha256": sha, "metadata": metadata}
        write_json(path, rows)


def recovery_source(root, filename):
    """Only use a source snapshot attached to these exact recovered bytes."""
    raw = str(filename or "").replace("\\", "/")
    output = (Path(root) / "output").resolve()
    candidate = Path(raw)
    if candidate.is_absolute():
        try:
            raw = candidate.resolve().relative_to(output).as_posix()
        except ValueError:
            return None
    if not raw.startswith("_recovery/"):
        return None
    path = scheduled_video_path(output, raw)
    with _LOCK:
        entry = read_json(Path(root) / "data" / "video_recovery_sources.json", {}).get(raw)
    if not entry or file_digest(path) != entry.get("sha256"):
        raise ValueError("MP4 phục hồi đã thay đổi hoặc mất thông tin nguồn; render lại từ video gốc.")
    return {**entry["metadata"], "clip_filename": raw}
