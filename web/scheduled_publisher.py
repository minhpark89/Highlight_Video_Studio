import json
import threading
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
POSTS_FILE = BASE_DIR / "posts.json"
POSTED_CLIPS_FILE = BASE_DIR / "posted_clips.json"
OUTPUT_DIR = BASE_DIR / "output"

_FILE_LOCK = threading.Lock()


def load_posts():
    with _FILE_LOCK:
        if not POSTS_FILE.exists():
            return []
        try:
            return json.loads(POSTS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []


def save_posts(posts):
    with _FILE_LOCK:
        POSTS_FILE.write_text(json.dumps(posts, indent=2, ensure_ascii=False), encoding="utf-8")


def _record_posted_clip(clip_filename):
    with _FILE_LOCK:
        posted_list = []
        if POSTED_CLIPS_FILE.exists():
            posted_list = json.loads(POSTED_CLIPS_FILE.read_text(encoding="utf-8"))
        if clip_filename not in posted_list:
            posted_list.append(clip_filename)
            POSTED_CLIPS_FILE.write_text(json.dumps(posted_list, indent=2), encoding="utf-8")


def process_scheduled_posts_once(poster=None, now=None, website_publisher=None, comment_generator=None):
    """Process one deterministic cycle while preserving the pre-publish claim lock."""
    import sys

    sys.path.insert(0, str(BASE_DIR))
    from src.publisher.first_comment_queue import enqueue_first_comment, process_due_first_comments
    from src.publisher.meta_reel_poster import MetaReelPoster
    from src.publisher.website_publisher import generate_curiosity_comment_with_llm, publish_clip_to_website_cms

    poster = poster or MetaReelPoster()
    website_publisher = website_publisher or publish_clip_to_website_cms
    comment_generator = comment_generator or generate_curiosity_comment_with_llm
    current_dt = now or datetime.now()

    queue_result = process_due_first_comments(poster, now=int(current_dt.timestamp()))
    posts = load_posts()
    posts_by_id = {post.get("id"): post for post in posts}
    for outcome in queue_result.get("outcomes", []):
        post = posts_by_id.get(outcome.get("post_id"))
        if not post:
            continue
        post["first_comment_status"] = outcome.get("status")
        post["first_comment_attempts"] = outcome.get("attempts")
        post["first_comment_error"] = outcome.get("last_error", "")
        if outcome.get("comment_id"):
            post["comment_id"] = outcome["comment_id"]

    claimed_posts = []
    for post in posts:
        if post.get("status") != "scheduled":
            continue
        scheduled_time = post.get("scheduled_time")
        if not scheduled_time:
            continue
        try:
            scheduled_dt = datetime.strptime(scheduled_time[:19], "%Y-%m-%d %H:%M:%S")
        except Exception:
            post["schedule_error"] = "Thời gian lên lịch không hợp lệ"
            continue
        if scheduled_dt <= current_dt:
            post["status"] = "publishing"
            post["claimed_at"] = current_dt.strftime("%Y-%m-%d %H:%M:%S")
            claimed_posts.append(post)

    if claimed_posts:
        save_posts(posts)

    for post in claimed_posts:
        post_id = post.get("id")
        page_id = post.get("page_id")
        clip_filename = post.get("media_file") or post.get("clip_filename")
        page_token = post.get("token")
        title = post.get("title", "")
        content = post.get("content", "")
        first_comment = post.get("first_comment", "")
        video_path = OUTPUT_DIR / clip_filename if clip_filename else None

        if not video_path or not video_path.exists():
            post.update({
                "status": "failed",
                "error": f"Không tìm thấy file video: {clip_filename}",
                "retryable": True,
                "retry_stage": "local_video",
            })
            continue

        if post.get("auto_first_comment", True):
            post["website_status"] = "generating"
            post["first_comment_status"] = "generating"
            try:
                cms_result = website_publisher(clip_filename, title)
                article_url = cms_result[0] if isinstance(cms_result, tuple) else str(cms_result)
                if not article_url:
                    raise RuntimeError("CMS không trả Website URL")
                post["article_url"] = article_url
                try:
                    first_comment = comment_generator(
                        title,
                        article_url,
                        enable_llm=post.get("use_llm_comment", True),
                    )
                except Exception:
                    first_comment = (
                        f"🔥 Watch the full uncut footage and breakdown here: {article_url}\n"
                        "👉 Scroll down the article to stream the complete high-definition video!"
                    )
                post["first_comment"] = first_comment
                post["website_status"] = "ready"
                post["first_comment_status"] = "ready"
            except Exception as exc:
                post.update({
                    "status": "failed",
                    "retryable": True,
                    "retry_stage": "website",
                    "website_status": "failed",
                    "website_error": str(exc),
                    "first_comment_status": "generation_failed",
                    "first_comment_error": str(exc),
                })
                continue
        elif first_comment:
            post["first_comment_status"] = "ready"
        else:
            post["first_comment_status"] = "not_configured"

        try:
            # The worker publishes first, then comments. Passing an empty comment
            # prevents MetaReelPoster from making an implicit/out-of-order call.
            result = poster.publish_reel(
                page_id=page_id,
                page_token=page_token,
                video_path=str(video_path),
                description=f"{title}\n\n{content}",
                first_comment="",
            )
            if not result.get("success"):
                post.update({
                    "status": "failed",
                    "retryable": True,
                    "retry_stage": "facebook_publish",
                    "error": result.get("error", "Lỗi Meta Graph API không xác định"),
                })
                continue

            facebook_id = result.get("video_id") or result.get("reel_id")
            post.update({
                "status": "published",
                "post_fb_id": facebook_id,
                "fb_url": result.get("fb_url") or (f"https://www.facebook.com/reel/{facebook_id}" if facebook_id else ""),
                "published_at": current_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "error": "",
            })

            if first_comment:
                comment_result = poster.post_first_comment(facebook_id, page_token, first_comment)
                if comment_result.get("success"):
                    post["comment_id"] = comment_result.get("comment_id")
                    post["first_comment_status"] = "posted"
                    post["first_comment_error"] = ""
                else:
                    queued = enqueue_first_comment(
                        facebook_id,
                        page_token,
                        first_comment,
                        int(current_dt.timestamp()) + 30,
                        post_id=post_id,
                    )
                    post["first_comment_status"] = "pending_retry"
                    post["first_comment_error"] = comment_result.get("error", "Không thể đăng First Comment")
                    post["first_comment_queue_id"] = queued.get("queue_id")

            _record_posted_clip(clip_filename)
        except Exception as exc:
            post.update({
                "status": "failed",
                "retryable": True,
                "retry_stage": "facebook_publish",
                "error": str(exc),
            })

    if claimed_posts or queue_result.get("changed"):
        save_posts(posts)
    return {"claimed": len(claimed_posts), "queue": queue_result, "posts": posts}


def scheduled_publisher_worker_loop():
    """Run publishing cycles continuously; all external calls remain in the cycle helper."""
    print("[ScheduledPublisher] Background publisher worker started with Idempotent Claim Lock!")
    while True:
        try:
            process_scheduled_posts_once()
        except Exception as exc:
            print(f"[ScheduledPublisher] Loop Error: {exc}")
        time.sleep(20)
