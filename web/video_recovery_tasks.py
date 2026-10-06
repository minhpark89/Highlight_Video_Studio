"""Persisted local render requests. A finished render never posts by itself."""
from datetime import datetime
from pathlib import Path
import threading
import uuid

from src.video_recovery_media import (read_json, write_json, recovery_interval,
    file_digest, save_recovery_source, checked_video)

_LOCK = threading.RLock()
_ACTIVE = set()


def _state_file(root):
    return Path(root) / "data" / "video_recovery_tasks.json"


def task_for(root, post_id):
    key = (str(Path(root).resolve()), post_id)
    with _LOCK:
        row = read_json(_state_file(root), {}).get(post_id)
        if row and row.get("status") in ("queued", "running") and key not in _ACTIVE:
            row.update(status="interrupted", message="Render bị gián đoạn khi app đóng; bấm Render lại để tiếp tục.")
        if row and row.get("status") == "ready":
            try:
                path, _ = checked_video(Path(root) / "output", row["filename"])
                if file_digest(path) != row.get("sha256"):
                    raise ValueError("changed")
            except (ValueError, OSError):
                row.update(status="error", message="File phục hồi thiếu hoặc đã thay đổi; render lại.")
        return row


def _update(root, post_id, **changes):
    with _LOCK:
        rows = read_json(_state_file(root), {})
        rows[post_id].update(changes, updated_at=datetime.now().isoformat(timespec="seconds"))
        write_json(_state_file(root), rows)


def start_task(root, post, *, render=None):
    root = Path(root).resolve()
    key = (str(root), post["id"])
    with _LOCK:
        if key in _ACTIVE:
            return task_for(root, post["id"])
        previous = task_for(root, post["id"])
        if previous and previous.get("status") == "ready":
            return previous
        if len(_ACTIVE) >= 2:
            raise ValueError("Đang render hai clip phục hồi; chờ một clip hoàn tất rồi thử lại.")
        rows = read_json(_state_file(root), {})
        task = {"id": uuid.uuid4().hex, "post_id": post["id"], "status": "queued",
                "original_filename": post.get("media_file") or post.get("clip_filename"),
                "video_id": str(post.get("meta_upload_video_id") or post.get("meta_video_id") or ""),
                "message": "Đang kiểm tra nguồn gốc và mốc cắt...", "created_at": datetime.now().isoformat(timespec="seconds")}
        rows[post["id"]] = task
        write_json(_state_file(root), rows)
        _ACTIVE.add(key)
        thread = threading.Thread(target=_render_task, args=(root, dict(post), task, render), daemon=True)
        try:
            thread.start()
        except Exception:
            _ACTIVE.discard(key)
            _update(root, post["id"], status="error", message="Không khởi động được render; thử lại.")
            raise
        return dict(task)


def _render_task(root, post, task, render):
    from src.publisher.website_publisher import get_clip_metadata, extract_youtube_video_id
    from src.media_validation import probe_video
    try:
        _update(root, post["id"], status="running")
        meta = get_clip_metadata(task["original_filename"])
        source = Path(str(meta.get("source_video_path") or meta.get("long_video_path") or ""))
        if not source.is_file() or source.is_symlink():
            raise ValueError("Video gốc không còn trong máy; chọn clip hợp lệ trong kho hoặc tải lại nguồn gốc.")
        if not (extract_youtube_video_id(meta.get("youtube_url")) or extract_youtube_video_id(meta.get("youtube_id"))):
            raise ValueError("Thiếu link video gốc cho embed Website; kiểm tra nguồn của job trước.")
        source_info = probe_video(source)
        start, end, adjusted = recovery_interval(meta, source_info["duration"])
        directory = root / "output" / "_recovery"
        directory.mkdir(parents=True, exist_ok=True)
        if directory.is_symlink() or directory.resolve().parent != (root / "output").resolve():
            raise ValueError("Thư mục phục hồi không hợp lệ.")
        filename = "_recovery/recovered-" + task["id"] + ".mp4"
        output = root / "output" / filename
        if render is None:
            from src.pipeline import render_highlight_clip
            render = render_highlight_clip
        _update(root, post["id"], clip_start=start, clip_end=end, interval_adjusted=adjusted,
                message="Đang render đoạn %.1f–%.1f giây từ nguồn gốc..." % (start, end))
        render(source_video=str(source), start_time=start, end_time=end, output_path=output,
               subtitle_style="none", update_status=lambda message: _update(root, post["id"], message=str(message)[:240]))
        _, info = checked_video(root / "output", filename, refresh=True)
        sha = file_digest(output)
        meta.update(clip_start=start, clip_end=end, recovery_original_filename=task["original_filename"],
                    recovery_post_id=post["id"], recovery_interval_adjusted=adjusted)
        save_recovery_source(root, filename, meta, sha)
        _update(root, post["id"], status="ready", filename=filename, sha256=sha, **info,
                title=meta.get("video_title") or "Video phục hồi", source_url=meta.get("youtube_url") or "",
                message="MP4 đã kiểm tra. Xem trước rồi chọn clip này để tạo lịch thay thế." +
                        (" Mốc cắt cũ vượt nguồn; đã chọn đoạn hợp lệ trong video gốc." if adjusted else ""))
    except Exception as exc:
        from web.meta_diagnostics import safe_error
        _update(root, post["id"], status="error", message=safe_error(exc))
    finally:
        with _LOCK:
            _ACTIVE.discard((str(root), post["id"]))
