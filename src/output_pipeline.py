"""Continuous output intake and explicitly opted-in daily posting plans.

SQLite owns source and slot claims. JSON queues remain the existing workers'
interface; deterministic post IDs let a interrupted claim repair that interface
without issuing another CMS or Meta request.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

from multi_pc.data_root import canonical_data_root
from multi_pc.json_io import replace_with_retry
from web.posts_store import load_posts_file, save_posts_file, _LOCK as POSTS_LOCK

ROOT = canonical_data_root(allow_repo_fallback=Path(__file__).resolve().parent.parent)
_LOCK = threading.RLock()
_THREAD = None
_OBSERVED = {}
_STATUS = {"alive": False, "last_cycle_at": "", "error": ""}
HELD_STATUSES = {"preparing", "draft", "reserved", "scheduled", "meta_handoff", "meta_scheduled",
                 "processing", "publishing", "published", "failed"}


def _read(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        replace_with_retry(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def settings(root=None):
    root = Path(root or ROOT)
    return {"enabled": True, "stable_seconds": 15, "max_backlog": 200,
            "min_free_gb": 2, "scan_batch": 16, "plans": [],
            **_read(root / "config" / "output_pipeline.json", {})}


def save_settings(value, root=None):
    root = Path(root or ROOT)
    with _LOCK:
        saved = settings(root)
        for key in ("enabled",):
            if key in value:
                if not isinstance(value[key], bool):
                    raise ValueError(f"{key} must be a boolean")
                saved[key] = value[key]
        for key, lower, upper in (("stable_seconds", 2, 600), ("max_backlog", 1, 10000),
                                  ("min_free_gb", 0, 1000), ("scan_batch", 1, 100)):
            if key in value:
                number = value[key]
                if isinstance(number, bool) or not isinstance(number, (int, float)) or not lower <= number <= upper:
                    raise ValueError(f"Invalid {key}")
                if key != "min_free_gb" and int(number) != number:
                    raise ValueError(f"{key} must be an integer")
                saved[key] = number
        _write(root / "config" / "output_pipeline.json", saved)
        return saved


def save_plan(plan, pages, groups, root=None):
    """Store explicit Page scope; old schedules/groups never imply opt-in."""
    root = Path(root or ROOT)
    if not isinstance(plan, dict):
        raise ValueError("Daily plan must be an object")
    for key in ("daily", "enabled"):
        if key in plan and not isinstance(plan[key], bool):
            raise ValueError(f"{key} must be a boolean")
    explicit = {str(pid) for pid in plan.get("explicit_page_ids", plan.get("page_ids", []))}
    selected = set(explicit)
    group_ids = [str(gid) for gid in plan.get("group_ids", [])]
    group_map = {str(g["id"]): g for g in groups}
    for gid in group_ids:
        if gid not in group_map:
            raise ValueError("Selected Page group no longer exists")
        selected.update(str(pid) for pid in group_map[gid].get("page_ids", []))
    page_map = {str(p["page_id"]): p for p in pages}
    if not selected or selected - page_map.keys():
        raise ValueError("Select existing Pages or Page groups for daily posting")
    slots = plan.get("slots") or ["11:30", "19:30"]
    normalized = []
    for slot in slots:
        try:
            parsed = datetime.strptime(str(slot).strip(), "%H:%M")
        except ValueError as exc:
            raise ValueError("Daily slots must use HH:MM") from exc
        normalized.append(parsed.strftime("%H:%M"))
    limit = plan.get("posts_per_day", len(normalized))
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= len(set(normalized)):
        raise ValueError("Posts per day must fit the selected daily slots")
    mode = plan.get("approval_mode", "manual")
    if mode not in ("manual", "automatic"):
        raise ValueError("Invalid draft review mode")
    publish_mode = plan.get("publish_mode", "app_queue")
    if publish_mode not in ("app_queue", "meta_scheduled"):
        raise ValueError("Invalid publishing mode")
    stagger = plan.get("stagger_minutes", 15)
    if isinstance(stagger, bool) or not isinstance(stagger, int) or not 1 <= stagger <= 1440:
        raise ValueError("Invalid posting interval")
    start_date = str(plan.get("start_date") or datetime.now().date().isoformat())
    datetime.strptime(start_date, "%Y-%m-%d")
    stored = {"id": str(plan.get("id") or "rules"), "enabled": plan.get("enabled", True),
              "daily": plan.get("daily", False), "approval_mode": mode, "publish_mode": publish_mode,
              "page_ids": sorted(selected), "explicit_page_ids": sorted(explicit), "group_ids": group_ids,
              "slots": sorted(set(normalized))[:limit], "posts_per_day": limit,
              "stagger_minutes": stagger, "start_date": start_date,
              "token_group_id": str(plan.get("token_group_id") or ""),
              "use_llm": plan.get("use_llm", True) is not False,
              "updated_at": datetime.now().isoformat(timespec="seconds")}
    with _LOCK:
        saved = settings(root)
        saved["plans"] = [p for p in saved["plans"] if p["id"] != stored["id"]] + [stored]
        _write(root / "config" / "output_pipeline.json", saved)
    return stored


@contextmanager
def _connect(root):
    directory = Path(root) / "data"
    directory.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(directory / "output_ledger.sqlite3"), timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=FULL")
    db.execute("""CREATE TABLE IF NOT EXISTS sources (
        sha256 TEXT PRIMARY KEY, path TEXT NOT NULL, post_id TEXT NOT NULL,
        assigned INTEGER NOT NULL DEFAULT 0, published INTEGER NOT NULL DEFAULT 0,
        receipt TEXT NOT NULL DEFAULT '', deleted_at TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
        intake TEXT NOT NULL DEFAULT '', interface_written INTEGER NOT NULL DEFAULT 0)""")
    db.execute("""CREATE TABLE IF NOT EXISTS slots (
        page_id TEXT NOT NULL, scheduled_time TEXT NOT NULL, sha256 TEXT NOT NULL UNIQUE,
        plan_id TEXT NOT NULL, assignment TEXT NOT NULL,
        PRIMARY KEY(page_id, scheduled_time))""")
    db.execute("CREATE TABLE IF NOT EXISTS identities (identity TEXT PRIMARY KEY, sha256 TEXT NOT NULL)")
    db.commit()
    try:
        with db:
            yield db
    finally:
        db.close()


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def claimed_hashes(root=None):
    with _LOCK, _connect(Path(root or ROOT)) as db:
        return {row[0] for row in db.execute("SELECT sha256 FROM sources WHERE assigned=1 OR published=1")} | {
            row[0].removeprefix('sha:') for row in db.execute(
                "SELECT identity FROM identities JOIN sources USING(sha256) WHERE identity LIKE 'sha:%' AND (assigned=1 OR published=1)")}


def source_identity_seen(job_id, clip_index, root=None):
    with _LOCK, _connect(Path(root or ROOT)) as db:
        return bool(db.execute("SELECT 1 FROM identities WHERE identity=?", (f"job:{job_id}/clip:{clip_index}",)).fetchone())


def reserve_batch(entries, root=None):
    """Fence the existing batch distributor with the same source ledger."""
    root = Path(root or ROOT)
    with _LOCK, _connect(root) as db:
        for post in entries:
            sha = post["source_sha256"]
            prior = db.execute("SELECT * FROM sources WHERE sha256=?", (sha,)).fetchone()
            if prior and (prior["assigned"] or prior["published"]):
                raise ValueError("Video đã được claim cho một bài/nhóm khác")
            if prior:
                post["id"] = prior["post_id"]
            snapshot = {key: value for key, value in post.items() if key not in ("token", "page_token", "access_token")}
            if prior:
                db.execute("UPDATE sources SET assigned=1,intake=?,interface_written=0 WHERE sha256=?",
                           (json.dumps(snapshot), sha))
            else:
                db.execute("INSERT INTO sources(sha256,path,post_id,assigned,intake,created_at) VALUES(?,?,?,1,?,?)",
                           (sha, str((root / "output" / post["media_file"]).resolve()), post["id"], json.dumps(snapshot),
                            datetime.now().isoformat(timespec="seconds")))


def finish_batch(root=None):
    root = Path(root or ROOT)
    with _LOCK, POSTS_LOCK, _connect(root) as db:
        written = {(p.get("id"), p.get("source_sha256"))
                   for p in load_posts_file(root / "posts.json")}
        for source in db.execute("SELECT post_id,sha256 FROM sources WHERE interface_written=0"):
            if (source["post_id"], source["sha256"]) in written:
                db.execute("UPDATE sources SET interface_written=1 WHERE sha256=?", (source["sha256"],))


def valid_mp4(path):
    from src.media_validation import valid_video
    return valid_video(path)


def pressure(root=None):
    root = Path(root or ROOT)
    cfg = settings(root)
    output = root / "output"
    output.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(output).free
    count = len([p for p in output.glob("*.mp4") if ".rendering." not in p.name])
    reason = ("disk_pressure" if free < cfg["min_free_gb"] * 1024**3 else
              "backlog_limit" if count >= cfg["max_backlog"] else "")
    return {"paused": bool(reason), "reason": reason, "backlog": count,
            "free_gb": round(free / 1024**3, 2), "max_backlog": cfg["max_backlog"]}


def _metadata(path, jobs):
    for job in jobs:
        for clip in job.get("clips", []):
            if Path(str(clip.get("filename") or "")).name == path.name:
                return {"title": clip.get("title") or job.get("video_title") or path.stem,
                        "summary": clip.get("reason", ""), "source_job_id": job.get("id", ""),
                        "source_clip_id": str(clip.get("clip_index", "")), "video_url": job.get("youtube_url", "")}
    return {"title": path.stem.replace("_", " "), "summary": ""}


def _assignment_candidates(plans, pages, groups, now, token_groups):
    from multi_pc.posting_schedule import paced_offsets_by_token
    page_map = {str(p["page_id"]): p for p in pages}
    group_map = {str(g["id"]): g for g in groups}
    for plan in plans:
        if not plan.get("enabled") or not plan.get("daily"):
            continue
        selected = set(plan.get("explicit_page_ids", plan["page_ids"]))
        for gid in plan["group_ids"]:
            if gid in group_map:
                selected.update(str(pid) for pid in group_map[gid].get("page_ids", []))
        allowed = set(plan["page_ids"]) & selected
        token_group = next((g for g in token_groups if str(g.get("id")) == plan.get("token_group_id")), None)
        if plan.get("token_group_id") and not token_group:
            continue
        if token_group:
            allowed &= {str(pid) for pid in token_group.get("page_ids", [])}
        scoped = [dict(page_map[pid]) for pid in sorted(allowed) if pid in page_map]
        if token_group:
            for page in scoped:
                binding = (token_group.get("page_token_bindings") or {}).get(str(page["page_id"]))
                if binding:
                    page["token_id"] = str(binding)
                if str(page.get("token_id")) not in {str(t) for t in token_group.get("token_ids", [])}:
                    page["token_id"] = ""
        scoped = [p for p in scoped if p.get("token_id")]
        offsets = paced_offsets_by_token([p["token_id"] for p in scoped], global_seconds=0,
                                        token_seconds=plan["stagger_minutes"] * 60)
        for day in (now.date(), (now + timedelta(days=1)).date()):
            if day.isoformat() < plan["start_date"]:
                continue
            for slot in plan["slots"]:
                base = datetime.combine(day, datetime.strptime(slot, "%H:%M").time())
                for page, offset in zip(scoped, offsets):
                    scheduled = base + timedelta(seconds=offset)
                    minimum = timedelta(minutes=20) if plan["publish_mode"] == "meta_scheduled" else timedelta(seconds=5)
                    if scheduled <= now + minimum:
                        continue
                    # A crowded token must not push a daily slot into another day.
                    if scheduled.date() != day:
                        continue
                    group = next((group_map[gid] for gid in plan["group_ids"] if gid in group_map
                                  and str(page["page_id"]) in {str(pid) for pid in group_map[gid].get("page_ids", [])}), {})
                    yield {"page_id": str(page["page_id"]), "page_name": page.get("page_name", ""),
                           "token_id": str(page["token_id"]), "group_id": group.get("id", ""),
                           "group_name": group.get("name", ""), "token_group_id": plan.get("token_group_id", ""),
                           "daily_plan_id": plan["id"], "post_daily": True, "use_llm": plan["use_llm"],
                           "approval_mode": plan["approval_mode"], "requested_publish_mode": plan["publish_mode"],
                           "token_gap_seconds": plan["stagger_minutes"] * 60,
                           "scheduled_time": scheduled.strftime("%Y-%m-%d %H:%M:%S")}


def process_once(*, root=None, pages=None, groups=None, token_groups=None, now=None, probe=valid_mp4):
    """One bounded local cycle: claim files, reserve slots, attach worker jobs."""
    from src import content_packages as packages
    root = Path(root or ROOT)
    now = now or datetime.now()
    cfg = settings(root)
    if not cfg["enabled"]:
        return {"imported": 0, "assigned": 0, "disabled": True}
    output = (root / "output").resolve()
    output.mkdir(parents=True, exist_ok=True)
    jobs = _read(root / "jobs.json", [])
    imported = assigned = 0
    with _LOCK, POSTS_LOCK, _connect(root) as db:
        posts = load_posts_file(root / "posts.json")
        for pending in db.execute("SELECT * FROM sources WHERE interface_written=0 AND intake!=''"):
            existing = next((p for p in posts if p.get("id") == pending["post_id"]), None)
            if not existing:
                posts.append(json.loads(pending["intake"]))
            elif pending["assigned"] and not existing.get("content_frozen_at") and existing.get("status") in ("preparing", "draft"):
                existing.update(json.loads(pending["intake"]))
        # Migrate existing assignments into the durable hash ledger while files
        # still exist, including drafts and remote handoffs.
        legacy_by_path = {}
        for post in posts:
            if post.get("status") not in HELD_STATUSES or post.get("output_pipeline"):
                continue
            raw = post.get("media_file") or post.get("clip_filename")
            if raw:
                candidate = Path(raw)
                candidate = (candidate if candidate.is_absolute() else output / candidate).resolve()
                legacy_by_path[str(candidate)] = post
            sha = post.get("source_sha256")
            if not sha and raw and candidate.is_file() and candidate.is_relative_to(output):
                observed = _OBSERVED.get(str(candidate))
                signature = (candidate.stat().st_size, candidate.stat().st_mtime_ns)
                sha = observed[2] if observed and observed[0] == signature and observed[2] else file_hash(candidate)
                post["source_sha256"] = sha
            if sha:
                db.execute("INSERT OR IGNORE INTO sources(sha256,path,post_id,assigned,created_at) VALUES(?,?,?,1,?)",
                           (sha, str(candidate) if raw else "", post["id"], now.isoformat()))
                source = db.execute("SELECT * FROM sources WHERE sha256=?", (sha,)).fetchone()
                if source and not source["assigned"]:
                    db.execute("UPDATE sources SET assigned=1 WHERE sha256=?", (sha,))
                    intake_post = next((p for p in posts if p.get("id") == source["post_id"]), None)
                    if intake_post and intake_post.get("output_pipeline") and not intake_post.get("page_id"):
                        intake_post.update({"status": "superseded", "superseded_by": post["id"]})
        scanned = 0
        for path in sorted(output.glob("*.mp4"), key=lambda p: p.stat().st_mtime):
            if ".rendering." in path.name or not path.resolve().is_relative_to(output):
                continue
            signature = (path.stat().st_size, path.stat().st_mtime_ns)
            key = str(path.resolve())
            prior = _OBSERVED.get(key)
            if not prior or prior[0] != signature:
                _OBSERVED[key] = (signature, time.monotonic(), "")
                continue
            if prior[2]:
                continue
            if time.monotonic() - prior[1] < cfg["stable_seconds"]:
                continue
            if scanned >= cfg["scan_batch"]:
                break
            scanned += 1
            if not probe(path):
                continue
            sha = file_hash(path)
            if (path.stat().st_size, path.stat().st_mtime_ns) != signature:
                continue
            legacy = legacy_by_path.get(key)
            if legacy:
                legacy["source_sha256"] = sha
            meta = _metadata(path, jobs)
            identity = (f"job:{meta['source_job_id']}/clip:{meta['source_clip_id']}"
                        if meta.get("source_job_id") and meta.get("source_clip_id") else "sha:" + sha)
            known = db.execute("SELECT * FROM sources WHERE sha256=? OR sha256 IN (SELECT sha256 FROM identities WHERE identity IN (?,?))",
                               (sha, identity, 'sha:' + sha)).fetchone()
            if not known:
                post_id = legacy["id"] if legacy else "output_" + sha[:32]
                db.execute("INSERT INTO sources(sha256,path,post_id,assigned,created_at) VALUES(?,?,?,?,?)",
                           (sha, key, post_id, int(bool(legacy)), now.isoformat()))
                if not legacy:
                    posts.append({"id": post_id, "media_file": path.name, "source_video_path": key,
                                  "source_sha256": sha, "output_pipeline": True, "type": "reel",
                                  "website_media_mode": "youtube",
                                  "title": meta["title"], "content": "", "hashtags": "",
                                  "status": "preparing", "approval_mode": "manual", "post_daily": False,
                                  "auto_first_comment": True, "use_llm_comment": True,
                                  "content_package_status": "queued", "website_status": "pending_generation",
                                  "first_comment_status": "pending_generation", "publish_mode": "app_queue",
                                  "created_at": now.isoformat(timespec="seconds"), **meta})
                    db.execute("UPDATE sources SET intake=? WHERE sha256=?", (json.dumps(posts[-1]), sha))
                    imported += 1
            elif not known["assigned"] and not known["published"]:
                # Recover an unassigned source renamed before approval.
                db.execute("UPDATE sources SET path=? WHERE sha256=?", (key, sha))
                row = next((p for p in posts if p.get("id") == known["post_id"]), None)
                if row and not (output / row["media_file"]).exists():
                    row.update({"media_file": path.name, "source_video_path": key})
            canonical_sha = known["sha256"] if known else sha
            db.execute("INSERT OR IGNORE INTO identities VALUES(?,?)", (identity, canonical_sha))
            db.execute("INSERT OR IGNORE INTO identities VALUES(?,?)", ('sha:' + sha, canonical_sha))
            _OBSERVED[key] = (signature, prior[1], sha)
        # Publish source claims before touching other queues. An interruption
        # after this point is repaired from deterministic post/slot identities.
        db.commit()
        for allocation in _assignment_candidates(cfg["plans"], pages or [], groups or [], now, token_groups or []):
            if db.execute("SELECT 1 FROM slots WHERE page_id=? AND scheduled_time=?",
                          (allocation["page_id"], allocation["scheduled_time"])).fetchone():
                continue
            if any(str(p.get("page_id")) == allocation["page_id"] and p.get("scheduled_time") == allocation["scheduled_time"]
                   and p.get("status") in HELD_STATUSES for p in posts):
                continue
            row = db.execute("SELECT * FROM sources WHERE assigned=0 AND published=0 ORDER BY created_at,sha256 LIMIT 1").fetchone()
            if not row:
                break
            post = next((p for p in posts if p.get("id") == row["post_id"]), None)
            if not post or not Path(row["path"]).is_file():
                # Deleted draft retains its claim; it cannot silently reappear.
                db.execute("UPDATE sources SET assigned=1 WHERE sha256=?", (row["sha256"],))
                continue
            db.execute("INSERT INTO slots VALUES(?,?,?,?,?)", (allocation["page_id"], allocation["scheduled_time"],
                       row["sha256"], allocation["daily_plan_id"], json.dumps(allocation)))
            db.execute("UPDATE sources SET assigned=1 WHERE sha256=? AND assigned=0", (row["sha256"],))
            post.update(allocation)
            assigned += 1
        db.commit()
        # Reapply a committed slot after a crash between SQLite and JSON saves.
        for slot in db.execute("SELECT sources.post_id, slots.assignment FROM slots JOIN sources USING(sha256)"):
            post = next((p for p in posts if p.get("id") == slot["post_id"]), None)
            if post and not post.get("daily_plan_id"):
                post.update(json.loads(slot["assignment"]))
        save_posts_file(root / "posts.json", posts)
        db.execute("UPDATE sources SET interface_written=1 WHERE interface_written=0")
    # Never hold the posts lock while acquiring the content lock: the content
    # worker applies results to posts after releasing its queue lock.
    for post in list(posts):
        if not post.get("output_pipeline") or post.get("content_frozen_at") or post.get("status") not in ("preparing", "draft"):
            continue
        package = packages.ensure_content_package(
            clip_filename=post["media_file"], source_sha256=post["source_sha256"], title=post["title"],
            summary=post.get("summary", ""), mode="auto" if post.get("use_llm", True) else "no_llm",
            post_ids=[post["id"]], create_website_article=True,
            schedule_priority=bool(post.get("page_id")), video_url=post.get("video_url", ""),
            source_job_id=post.get("source_job_id", ""), source_clip_id=post.get("source_clip_id", ""))
        with POSTS_LOCK:
            current = load_posts_file(root / "posts.json")
            row = next((p for p in current if p.get("id") == post["id"]), None)
            if row:
                row.update({"content_package_id": package["id"], "content_package_status": package["status"]})
                save_posts_file(root / "posts.json", current)
        if package["status"] == "ready":
            packages._apply_to_posts(package)
    return {"imported": imported, "assigned": assigned, **pressure(root)}


def record_receipt(sha, posts, root=None):
    if not sha:
        return False
    with _connect(Path(root or ROOT)) as db:
        first = posts[0]
        db.execute("INSERT OR IGNORE INTO sources(sha256,path,post_id,assigned,created_at) VALUES(?,?,?,1,?)",
                   (sha, str(first.get("source_video_path") or first.get("media_file") or ''), first['id'],
                    datetime.now().isoformat(timespec="seconds")))
        db.execute("UPDATE sources SET published=1, receipt=? WHERE sha256=?",
                   (json.dumps([{k: p.get(k) for k in ("id", "page_id", "group_id", "content_package_id", "post_fb_id",
                                                    "meta_video_id", "published_at", "article_url")} for p in posts]), sha))
        return bool(db.execute("SELECT 1 FROM sources WHERE sha256=? AND published=1", (sha,)).fetchone())


def review_draft(post_id, changes, pages, *, approve=False, root=None, now=None):
    root = Path(root or ROOT)
    now = now or datetime.now()
    with _LOCK, POSTS_LOCK, _connect(root) as db:
        posts = load_posts_file(root / "posts.json")
        post = next((p for p in posts if p.get("id") == post_id), None)
        if not post:
            raise ValueError("Không tìm thấy Draft")
        if not post.get("output_pipeline") or post.get("status") not in ("draft", "preparing") or post.get("content_frozen_at"):
            raise ValueError("Bài không còn ở Draft để chỉnh sửa/duyệt")
        for key in ("title", "content", "hashtags", "first_comment"):
            if key in changes:
                post[key] = str(changes[key]).strip()
        if approve and not (post.get("content_package_status") == "ready" and post.get("website_status") == "ready"
                and (post.get("website_video_status") == "verified" or
                     (post.get("website_media_mode") == "youtube" and post.get("website_video_status") == "youtube_embed_verified"))
                and post.get("article_url")
                and str(post.get("first_comment") or "").count(post["article_url"]) == 1
                and post.get("content") and post.get("title")):
            raise ValueError("Chờ package, video gốc trong bài Website và First Comment hoàn tất trước khi duyệt")
        page_id = str(changes.get("page_id", post.get("page_id")) or "")
        page = next((p for p in pages if str(p.get("page_id")) == page_id), None)
        if (approve or page_id) and (not page or not page.get("token_id")):
            raise ValueError("Chọn Page đã gán Token trước khi duyệt")
        scheduled = str(changes.get("scheduled_time", post.get("scheduled_time")) or "").strip()
        if scheduled:
            due = datetime.fromisoformat(scheduled)
            if due.tzinfo is not None:
                due = due.astimezone().replace(tzinfo=None)
            if due <= now:
                raise ValueError("Thời gian hẹn lịch phải ở tương lai")
        else:
            due = now if approve else None
        requested_mode = post.get("requested_publish_mode", "app_queue") if scheduled else "app_queue"
        if approve and requested_mode == "meta_scheduled":
            from multi_pc.meta_scheduling import parse_meta_schedule_time
            parse_meta_schedule_time(due.strftime("%Y-%m-%d %H:%M:%S"), now_ts=now.timestamp())
        source = db.execute("SELECT * FROM sources WHERE sha256=?", (post["source_sha256"],)).fetchone()
        if not source or source["published"]:
            raise ValueError("Source đã đăng hoặc không còn claim hợp lệ")
        assigned_time = due.strftime("%Y-%m-%d %H:%M:%S") if due else ""
        if page_id and assigned_time and any(p.get("id") != post_id and str(p.get("page_id")) == page_id
                and p.get("scheduled_time") == assigned_time and p.get("status") in HELD_STATUSES for p in posts):
            raise ValueError("Page đã có bài ở khung giờ này; chọn giờ khác")
        assignment = {"page_id": page_id, "page_name": (page or {}).get("page_name", page_id),
                      "token_id": (page or {}).get("token_id", ""), "scheduled_time": assigned_time,
                      "approval_mode": "manual", "requested_publish_mode": requested_mode}
        if page_id == str(post.get("page_id") or "") and post.get("token_group_id"):
            # Preserve the credential selected for this token group's Page.
            assignment["token_id"] = post.get("token_id") or assignment["token_id"]
        elif page_id != str(post.get("page_id") or ""):
            assignment.update({"token_group_id": "", "group_id": "", "group_name": ""})
        existing_slot = db.execute("SELECT * FROM slots WHERE sha256=?", (post["source_sha256"],)).fetchone()
        if not page_id or not assigned_time:
            db.execute("DELETE FROM slots WHERE sha256=?", (post["source_sha256"],))
        elif existing_slot:
            db.execute("UPDATE slots SET page_id=?, scheduled_time=?, assignment=? WHERE sha256=?",
                       (page_id, assigned_time, json.dumps(assignment), post["source_sha256"]))
        else:
            db.execute("INSERT INTO slots VALUES(?,?,?,?,?)", (page_id, assigned_time, post["source_sha256"],
                       "manual", json.dumps(assignment)))
        db.execute("UPDATE sources SET assigned=1 WHERE sha256=?", (post["source_sha256"],))
        post.update(assignment)
        post["draft_edited_at"] = now.isoformat(timespec="seconds")
        if approve:
            post.update({"status": "scheduled", "content_frozen_at": now.isoformat(timespec="seconds"),
                         "approved_at": now.isoformat(timespec="seconds"), "first_comment_snapshot": post["first_comment"]})
        # Commit the recovery snapshot before the JSON interface, as with intake.
        db.execute("UPDATE sources SET intake=?,interface_written=0 WHERE sha256=?", (json.dumps(post), post["source_sha256"]))
        db.commit()
        save_posts_file(root / "posts.json", posts)
        db.execute("UPDATE sources SET interface_written=1 WHERE sha256=?", (post["source_sha256"],))
        return dict(post)


def status(root=None):
    return {**_STATUS, "alive": bool(_THREAD and _THREAD.is_alive()), **pressure(root), "settings": settings(root)}


def _worker_loop():
    from multi_pc.data_root import ProcessLease
    from src.publisher.page_manager import PageManager
    lease = ProcessLease("output-pipeline", ROOT, stale_after=120)
    if not lease.acquire():
        return
    try:
        manager = PageManager(ROOT)
        from src.content_packages import start_content_package_worker
        start_content_package_worker()
        while True:
            lease.touch()
            try:
                process_once(pages=manager.list_pages(), groups=manager.list_groups(),
                             token_groups=_read(ROOT / "token_groups.json", []))
                _STATUS.update({"error": "", "last_cycle_at": datetime.now().isoformat(timespec="seconds")})
            except Exception as exc:
                from src.content_packages import sanitize_error
                _STATUS["error"] = sanitize_error(exc)
            time.sleep(3)
    finally:
        lease.release()


def start_worker():
    global _THREAD
    with _LOCK:
        if not _THREAD or not _THREAD.is_alive():
            _THREAD = threading.Thread(target=_worker_loop, daemon=True, name="output-pipeline")
            _THREAD.start()
        return _THREAD
