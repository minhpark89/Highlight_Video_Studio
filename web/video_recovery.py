"""Prepare local retries only after explicit, fresh rejection evidence."""
import hashlib
from datetime import datetime

from multi_pc.meta_scheduling import parse_meta_schedule_time
from src.content_packages import scheduled_video_path
from src.english_text import assert_english
from src.media_validation import probe_video


def can_replace_failed_video(post, seen):
    video_id = str(post.get("meta_upload_video_id") or post.get("meta_video_id") or "")
    return bool(video_id and post.get("status") in ("processing", "failed")
                and not post.get("replacement_post_id") and not post.get("post_fb_id")
                and not post.get("meta_cancel_requested")
                and seen.get("http_status") == 200 and str(seen.get("id")) == video_id
                and not seen.get("error") and not seen.get("error_code")
                and seen.get("copyright_matches") is False and seen.get("uploading_status") == "complete"
                and (seen.get("video_status") in ("error", "failed") or
                     seen.get("processing_status") in ("error", "failed"))
                and seen.get("publishing_status") in ("not_started", "error", "failed", "rejected"))


def prepare_replacement(posts, post, seen, output_dir, *, filename, schedule_time=None, mode="meta_scheduled"):
    existing = next((p for p in posts if p.get("id") == post.get("replacement_post_id")), None)
    if existing:
        return existing, False
    if not can_replace_failed_video(post, seen):
        raise ValueError("Meta chưa xác nhận video lỗi và chưa đăng; giữ ID cũ để đối soát.")
    path = scheduled_video_path(output_dir, filename)
    info = probe_video(path)
    if mode not in ("meta_scheduled", "app_queue"):
        raise ValueError("Chọn App đăng lại hoặc Meta giữ lịch.")
    if mode == "meta_scheduled":
        publish_at = parse_meta_schedule_time(schedule_time)
    elif schedule_time:
        due = datetime.fromisoformat(str(schedule_time).replace(" ", "T"))
        if due <= datetime.now():
            raise ValueError("Chọn giờ đăng mới chưa qua hoặc Đăng lại bằng App.")
        publish_at = due.timestamp()
    else:
        publish_at = datetime.now().timestamp()
    url = str(post.get("article_url") or "").strip()
    comment = str(post.get("first_comment_snapshot") or post.get("first_comment") or "").strip()
    if post.get("website_status") != "ready" or not url or comment.count(url) != 1:
        raise ValueError("Sửa Website và First Comment chứa đúng một link trước khi tạo lịch thay thế.")
    for field in ("title", "content"):
        assert_english(post.get(field, ""), field)
    assert_english(comment, "First Comment")
    if any(p.get("id") != post.get("id") and p.get("page_id") == post.get("page_id")
           and p.get("media_file") == path.name and p.get("status") in
           ("scheduled", "meta_handoff", "processing", "meta_scheduled", "publishing", "published") for p in posts):
        raise ValueError("Video này đã có bài hoặc lịch trên Page; kiểm tra bài hiện có.")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    stamp = datetime.now().isoformat(timespec="seconds")
    fields = ("title", "content", "hashtags", "type", "page_id", "page_name", "group_id", "group_name",
              "token_id", "token_name", "article_url", "website_status", "website_embed_status", "youtube_id", "video_url",
              "website_video_status", "website_video_url", "website_video_source", "website_thumbnail_url",
              "first_comment_profile_id", "first_comment_source", "first_comment_model", "content_package_source")
    replacement = {key: post[key] for key in fields if key in post}
    replacement.update(id=post["id"] + "_replacement", status="meta_handoff" if mode == "meta_scheduled" else "scheduled", publish_mode=mode,
        media_file=path.name, scheduled_time=datetime.fromtimestamp(publish_at).strftime("%Y-%m-%d %H:%M:%S"),
        created_at=stamp, content_frozen_at=stamp, first_comment=comment, first_comment_snapshot=comment,
        first_comment_status="ready", retryable=False, outcome_unknown=False, error="",
        meta_schedule_status="handoff_queued" if mode == "meta_scheduled" else "", replaces_post_id=post["id"],
        replacement_video_sha256=digest.hexdigest(), replacement_video_duration=info["duration"])
    if post.get("meta_recovery_token_id"):
        replacement["token_id"] = post["meta_recovery_token_id"]
    post.update(status="superseded", replacement_post_id=replacement["id"], superseded_at=stamp,
                meta_observation=seen, retryable=False,
                error="Video cũ được Meta xác nhận lỗi; đã tạo lịch thay thế bằng MP4 đã kiểm tra.")
    posts.insert(0, replacement)
    return replacement, True
