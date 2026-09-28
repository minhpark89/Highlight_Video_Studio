import json
import re
import threading
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
POSTS_FILE = BASE_DIR / "posts.json"
POSTED_CLIPS_FILE = BASE_DIR / "posted_clips.json"
OUTPUT_DIR = BASE_DIR / "output"
SCHEDULER_HEARTBEAT_FILE = BASE_DIR / "data" / "scheduler_heartbeat.json"

_FILE_LOCK = threading.Lock()
CYCLE_INTERVAL_SECONDS = 20
CLAIM_STALE_AFTER_SECONDS = 300
OVERDUE_GRACE_SECONDS = 120

# Workers sharing one loop (Flask dev server vs packaged waitress) must not double-claim.
_worker_lock = threading.Lock()
_worker_started = False

_heartbeat = {
    "running": False,
    "started_at": "",
    "last_cycle_at": "",
    "last_cycle_ok": None,
    "last_error": "",
    "cycles": 0,
    "jitter_threshold_seconds": OVERDUE_GRACE_SECONDS,
    "interval_seconds": CYCLE_INTERVAL_SECONDS,
}
_heartbeat_lock = threading.Lock()

_SECRET_PATTERNS = (
    re.compile(r"(access_token|page_token|token|api_key|apikey|secret|password|authorization)[=:\s]+[^\s&\"',]+", re.IGNORECASE),
    re.compile(r"([?&](?:access_token|token|api_key|key)=)[^\s&\"']+", re.IGNORECASE),
    re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]+", re.IGNORECASE),
)


def sanitize_error(message, limit=400):
    """Redact token-like values so operator-visible errors never leak credentials."""
    text = str(message or "")
    for pattern in _SECRET_PATTERNS:
        if pattern.groups >= 2:
            text = pattern.sub(lambda m: m.group(1) + "[redacted]", text)
        else:
            text = pattern.sub(lambda m: m.group(1) + "[redacted]" if m.groups() else "[redacted]", text)
    text = " ".join(text.split())
    return text[:limit]


def worker_status():
    with _heartbeat_lock:
        snapshot = dict(_heartbeat)
    snapshot["thread_alive"] = bool(_worker_thread and _worker_thread.is_alive())
    return snapshot


def _touch_heartbeat(ok, error=""):
    with _heartbeat_lock:
        _heartbeat["running"] = True
        _heartbeat["last_cycle_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _heartbeat["last_cycle_ok"] = ok
        _heartbeat["last_error"] = sanitize_error(error) if error else ""
        _heartbeat["cycles"] += 1
    try:
        SCHEDULER_HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
        SCHEDULER_HEARTBEAT_FILE.write_text(json.dumps(worker_status(), indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


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


def process_scheduled_posts_once(
    poster=None,
    now=None,
    website_publisher=None,
    comment_generator=None,
    force_due=False,
):
    """Process one deterministic cycle while preserving the pre-publish claim lock.

    ``force_due`` lets an operator run overdue posts immediately from the UI when
    the background worker missed a cycle; it never bypasses the claim/duplicate guards.
    """
    import sys

    sys.path.insert(0, str(BASE_DIR))
    from src.publisher.first_comment_queue import enqueue_first_comment, process_due_first_comments
    from src.publisher.meta_reel_poster import MetaReelPoster
    from src.publisher.website_publisher import generate_curiosity_comment_with_llm, publish_clip_to_website_cms

    poster = poster or MetaReelPoster()
    website_publisher = website_publisher or publish_clip_to_website_cms
    comment_generator = comment_generator or generate_curiosity_comment_with_llm
    current_dt = now or datetime.now()
    now_ts = current_dt.timestamp()

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

    # Recover records left in "publishing" by a crashed or killed cycle so they are
    # retried instead of hanging forever with a stale claim.
    recovered = 0
    for post in posts:
        if post.get("status") != "publishing":
            continue
        claimed_at = _parse_scheduled_time(post.get("claimed_at"))
        if claimed_at is not None and (now_ts - claimed_at.timestamp()) < CLAIM_STALE_AFTER_SECONDS:
            continue
        post.update({
            "status": "scheduled",
            "retryable": True,
            "retry_stage": post.get("retry_stage") or "claim_recovery",
            "recovered_at": current_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "error": "Khoi phuc bai dang bi ket o trang thai publishing (worker dung dot ngot)",
        })
        recovered += 1

    claimed_posts = []
    for post in posts:
        if post.get("status") != "scheduled":
            continue
        scheduled_time = post.get("scheduled_time")
        if not scheduled_time:
            continue
        scheduled_dt = _parse_scheduled_time(scheduled_time)
        if scheduled_dt is None:
            post["schedule_error"] = "Thời gian lên lịch không hợp lệ"
            continue
        if scheduled_dt <= current_dt:
            post["status"] = "publishing"
            post["claimed_at"] = current_dt.strftime("%Y-%m-%d %H:%M:%S")
            claimed_posts.append(post)

    if claimed_posts or recovered:
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

    if claimed_posts or recovered or queue_result.get("changed"):
        save_posts(posts)
    return {"claimed": len(claimed_posts), "recovered": recovered, "queue": queue_result, "posts": posts}


def scheduled_publisher_worker_loop():
    """Run publishing cycles continuously; all external calls remain in the cycle helper."""
    global _worker_started
    if not _worker_lock.acquire(blocking=False):
        print("[ScheduledPublisher] Worker loop already running in this process; skipping duplicate start.")
        return
    _worker_started = True
    with _heartbeat_lock:
        _heartbeat["started_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("[ScheduledPublisher] Background publisher worker started with Idempotent Claim Lock!")
    try:
        while True:
            try:
                result = process_scheduled_posts_once()
                _touch_heartbeat(True)
                if result.get("claimed") or result.get("recovered"):
                    print(f"[ScheduledPublisher] cycle claimed={result.get('claimed')} recovered={result.get('recovered')}")
            except Exception as exc:
                _touch_heartbeat(False, exc)
                print(f"[ScheduledPublisher] Loop Error: {sanitize_error(exc)}")
            time.sleep(CYCLE_INTERVAL_SECONDS)
    finally:
        _worker_started = False
        with _heartbeat_lock:
            _heartbeat["running"] = False
        _worker_lock.release()


def _parse_scheduled_time(value):
    """Parse stored naive local timestamps without raising on bad data."""
    if value is None:
        return None
    text = str(value).strip().replace("T", " ")
    if not text:
        return None
    if len(text) == 16:
        text += ":00"
    try:
        return datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


_worker_thread = None


def start_worker_thread():
    """Idempotently start the background worker; safe to call from app and packaged entrypoint."""
    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        return _worker_thread
    _worker_thread = threading.Thread(target=scheduled_publisher_worker_loop, daemon=True, name="scheduled-publisher")
    _worker_thread.start()
    return _worker_thread
