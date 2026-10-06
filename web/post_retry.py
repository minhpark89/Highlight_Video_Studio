"""Retry a rejected local row without releasing any existing Meta upload fence."""
import re
from datetime import datetime
from pathlib import Path

from multi_pc.meta_scheduling import parse_meta_schedule_time
from src.content_packages import scheduled_video_path
from src.english_text import assert_english
from src.media_validation import probe_video

REMOTE_FIELDS = ("meta_upload_video_id", "meta_video_id", "meta_post_id", "post_fb_id", "reel_id")


def can_retry_without_upload(post):
    if (post.get("status") != "failed" or not post.get("retryable") or post.get("outcome_unknown")
            or post.get("meta_cancel_requested") or any(post.get(k) for k in REMOTE_FIELDS)):
        return False
    stage = post.get("retry_stage")
    if stage in ("meta_preflight", "local_video", "website_content", "invalid_media", "recovery_schedule"):
        return True
    # Historical rows did not store a structured Init receipt. A definitive
    # 4xx rejection is different from a timeout after starting an upload.
    return bool(stage in ("facebook_publish", "meta_schedule_rejected") and
                (post.get("publish_error_code") == "meta_init_rejected" or
                 re.match(r"Meta init rejected \(HTTP 4\d\d\):", str(post.get("error") or ""))))


def prepare_retry(post, posts, output_dir, *, mode, schedule_time=None, now=None):
    if not can_retry_without_upload(post):
        raise ValueError("Bài đã có ID Meta, chưa rõ kết quả hoặc không còn là lỗi có thể thử lại; kiểm tra bài hiện có.")
    now = now or datetime.now()
    if mode not in ("app_queue", "meta_scheduled"):
        raise ValueError("Chọn App giữ lịch hoặc Meta giữ lịch.")
    path = scheduled_video_path(output_dir, post.get("media_file") or post.get("clip_filename"))
    probe_video(path)
    url = str(post.get("article_url") or "").strip()
    comment = str(post.get("first_comment_snapshot") or post.get("first_comment") or "").strip()
    if post.get("website_status") != "ready" or not url or comment.count(url) != 1:
        raise ValueError("Sửa Website và First Comment chứa đúng một URL trước khi thử đăng lại.")
    for field in ("title", "content"):
        assert_english(post.get(field) or "", field)
    assert_english(comment, "First Comment")
    for other in posts:
        same_media = Path(other.get("media_file") or other.get("clip_filename") or "").name.casefold() == path.name.casefold()
        same_hash = post.get("source_sha256") and other.get("source_sha256") == post.get("source_sha256")
        if (other.get("id") != post.get("id") and other.get("page_id") == post.get("page_id") and
                (same_media or same_hash) and (other.get("outcome_unknown") or any(other.get(k) for k in REMOTE_FIELDS)
                or other.get("status") in ("scheduled", "meta_handoff", "publishing", "processing", "meta_scheduled", "published"))):
            raise ValueError("Video này đã có bài/lịch khác trên Page; mở bài hiện có để tránh đăng trùng.")
    if mode == "meta_scheduled":
        due = datetime.fromtimestamp(parse_meta_schedule_time(schedule_time, now_ts=now.timestamp()))
    elif schedule_time:
        due = datetime.fromisoformat(str(schedule_time).replace(" ", "T"))
        if due <= now:
            raise ValueError("Giờ đăng đã qua; chọn giờ mới hoặc Đăng ngay qua App.")
    else:
        due = now
    post.setdefault("original_scheduled_time", post.get("scheduled_time"))
    post.setdefault("publish_retry_history", []).append({"at": now.isoformat(timespec="seconds"),
        "stage": post.get("retry_stage"), "error": post.get("error"), "previous_time": post.get("scheduled_time")})
    for key in ("publish_started_at", "claimed_at", "next_retry_at", "meta_scheduled_publish_time", "meta_next_check_at"):
        post.pop(key, None)
    post.update(status="meta_handoff" if mode == "meta_scheduled" else "scheduled",
                publish_mode=mode, requested_publish_mode=mode, scheduled_time=due.strftime("%Y-%m-%d %H:%M:%S"),
                retryable=False, outcome_unknown=False, error="", retry_stage="", publish_error_code="",
                meta_handoff_error="", first_comment=comment, first_comment_snapshot=comment,
                first_comment_status="ready", content_frozen_at=post.get("content_frozen_at") or now.isoformat(timespec="seconds"))
    if mode == "meta_scheduled":
        post["meta_schedule_status"] = "handoff_queued"
    return post
