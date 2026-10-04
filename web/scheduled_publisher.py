import json
import re
import threading
import time
from datetime import datetime
from pathlib import Path

# One canonical queue path per installation; a packaged entrypoint and a dev server
# must never claim from two different posts.json files.
try:
    from web.posts_store import canonical_posts_file
except ImportError:
    from posts_store import canonical_posts_file

from multi_pc.data_root import ProcessLease
from multi_pc.posting_schedule import next_paced_due_post

BASE_DIR = Path(__file__).resolve().parent.parent
POSTS_FILE = canonical_posts_file()
POSTED_CLIPS_FILE = POSTS_FILE.parent / "posted_clips.json"
OUTPUT_DIR = BASE_DIR / "output"
SCHEDULER_HEARTBEAT_FILE = BASE_DIR / "data" / "scheduler_heartbeat.json"

_FILE_LOCK = threading.Lock()
_cycle_lock = threading.Lock()
CYCLE_INTERVAL_SECONDS = 20
_active_posts = set()
_active_posts_lock = threading.Lock()
CLAIM_STALE_AFTER_SECONDS = 300
OVERDUE_GRACE_SECONDS = 120

# Workers sharing one loop (Flask dev server vs packaged waitress) must not double-claim.
_worker_lock = threading.Lock()
_worker_started = False
_worker_waiting_for_lease = False

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


def _safe_log(message):
    """Log without letting a closed/invalid stdout handle kill a worker cycle.

    Packaged startup can replace or close the process stdout while this daemon
    thread keeps running; an unguarded print() would then raise OSError and be
    reported as a cycle failure, hiding the real scheduler state.
    """
    try:
        print(message)
    except Exception:
        pass


def worker_status():
    with _heartbeat_lock:
        snapshot = dict(_heartbeat)
    snapshot["thread_alive"] = bool(_worker_thread and _worker_thread.is_alive())
    snapshot["waiting_for_lease"] = _worker_waiting_for_lease
    snapshot["cycle_active"] = _cycle_lock.locked()
    with _active_posts_lock:
        snapshot["active_posts"] = len(_active_posts)
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
    try:
        from web.posts_store import load_posts_file
    except ImportError:
        from posts_store import load_posts_file
    return load_posts_file(POSTS_FILE)


def save_posts(posts):
    try:
        from web.posts_store import save_posts_file
    except ImportError:
        from posts_store import save_posts_file
    save_posts_file(POSTS_FILE, posts)


def _record_posted_clip(clip_filename):
    with _FILE_LOCK:
        posted_list = []
        if POSTED_CLIPS_FILE.exists():
            posted_list = json.loads(POSTED_CLIPS_FILE.read_text(encoding="utf-8"))
        if not isinstance(posted_list, list):
            raise ValueError("posted_clips ledger must be a JSON array")
        if clip_filename not in posted_list:
            posted_list.append(clip_filename)
            temp = POSTED_CLIPS_FILE.with_name(POSTED_CLIPS_FILE.name + ".tmp")
            try:
                temp.write_text(json.dumps(posted_list, indent=2), encoding="utf-8")
                temp.replace(POSTED_CLIPS_FILE)
            finally:
                temp.unlink(missing_ok=True)


def remove_posted_clip_file(clip_filename, posts):
    """Remove only a confirmed published clip inside this installation output."""
    raw = str(clip_filename or "").strip()
    if not raw:
        return False
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = OUTPUT_DIR / candidate
    candidate = candidate.resolve()
    root = OUTPUT_DIR.resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        return False
    def same_clip(post):
        value = str(post.get("media_file") or post.get("clip_filename") or "").strip()
        if not value:
            return False
        path = Path(value)
        return (path if path.is_absolute() else OUTPUT_DIR / path).resolve() == candidate
    users = [post for post in posts if same_clip(post)]
    if not users or any(post.get("status") != "published" or not post.get("post_fb_id") for post in users):
        return False
    if any(post.get("auto_first_comment") and post.get("website_status") in ("pending_generation", "failed") for post in users):
        return False
    try:
        if raw not in json.loads(POSTED_CLIPS_FILE.read_text(encoding="utf-8")):
            return False
    except (OSError, ValueError):
        return False
    try:
        candidate.unlink()
        return True
    except OSError:
        return False


def _process_scheduled_posts_once(
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
    from src.publisher.page_manager import PageManager
    from src.publisher.token_vault import TokenVault
    from src.publisher.meta_preflight import preflight_pages
    from src.publisher.website_publisher import generate_curiosity_comment_with_llm, publish_clip_to_website_cms
    from src.content_packages import scheduled_video_path

    website_publisher = website_publisher or publish_clip_to_website_cms
    comment_generator = comment_generator or generate_curiosity_comment_with_llm
    page_manager = PageManager(BASE_DIR)
    token_vault = TokenVault(BASE_DIR)
    poster = poster or MetaReelPoster(token_vault=token_vault)
    current_dt = now or datetime.now()
    now_ts = current_dt.timestamp()

    posts = load_posts()
    posts_by_id = {post.get("id"): post for post in posts}
    def prepare_first_comment(item):
        linked_post = posts_by_id.get(item.get("post_id"))
        exact_token_id = str(item.get("token_id") or (linked_post or {}).get("token_id") or "")
        page_token = item.get("page_token")
        if exact_token_id:
            page = next((page for page in page_manager.list_pages()
                         if str(page.get("page_id")) == str((linked_post or {}).get("page_id"))), None)
            exact_page = {**page, "token_id": exact_token_id} if page else None
            verdict = preflight_pages([exact_page], token_vault, page_manager) if exact_page else {"ok": False}
            if not verdict.get("ok"):
                return {"ready": False, "error": "Exact First Comment credential unavailable; restore and Sync Page."}
            page_token = verdict["ready"][0]["token"]
        if linked_post and linked_post.get("publish_mode") == "meta_scheduled":
            check = MetaReelPoster(token_vault=token_vault).check_processing_reel(
                item.get("meta_video_id") or item.get("object_id"), page_token, exact_token_id or None,
            )
            if not check.get("verified"):
                return {"ready": False, "error": "Waiting for independently verified Meta publication."}
        return {"ready": bool(page_token), "page_token": page_token}
    queue_result = process_due_first_comments(poster, now=int(current_dt.timestamp()), prepare=prepare_first_comment)
    reconciled = 0
    for post in posts:
        if post.get("status") not in ("processing", "meta_scheduled") or not (post.get("meta_video_id") or post.get("meta_upload_video_id") or post.get("meta_post_id")):
            continue
        meta_scheduled = post.get("publish_mode") == "meta_scheduled" or bool(post.get("meta_scheduled_publish_time"))
        if meta_scheduled:
            publish_at = float(post.get("meta_scheduled_publish_time") or 0)
            if post.get("status") == "meta_scheduled" and publish_at and now_ts < publish_at + 90:
                continue
            if now_ts < float(post.get("meta_next_check_at") or 0):
                continue
        attempts = int(post.get("meta_reconcile_attempts") or 0)
        if now_ts < float(post.get("meta_next_check_at") or 0) and post.get("meta_reconcile_version") == 2:
            continue
        # New records require the same exact Page/token mapping as publishing.
        page = next((p for p in page_manager.list_pages() if str(p.get("page_id")) == str(post.get("page_id"))), None)
        exact_page = {**page, "token_id": post["token_id"]} if page and post.get("token_id") else None
        verdict = preflight_pages([exact_page], token_vault, page_manager) if exact_page else {"ok": False}
        if not verdict.get("ok"):
            post["meta_reconcile_error"] = "Exact Page credential unavailable; read-only verification paused."
            continue
        credential = verdict["ready"][0]
        from src.publisher.meta_reel_poster import MetaReelPoster as _MetaReelPoster
        # Meta finish can return a post_id that rejects video-status fields.
        # The upload video_id is the actual Reel object and is read first.
        poster_for_check = _MetaReelPoster(token_vault=token_vault)
        check = {"verified": False}
        for candidate in dict.fromkeys((post.get("meta_video_id"), post.get("meta_upload_video_id"), post.get("meta_post_id"))):
            if candidate:
                if meta_scheduled:
                    check = poster_for_check.check_scheduled_reel(
                        candidate, credential["token"], post.get("meta_scheduled_publish_time"), credential["token_id"]
                    )
                    if check.get("status") == "published" and not check.get("verified"):
                        public_check = poster_for_check.check_processing_reel(
                            candidate, credential["token"], credential["token_id"]
                        )
                        if public_check.get("verified"):
                            check = {**public_check, "verified": True, "status": "published"}
                else:
                    check = poster_for_check.check_processing_reel(
                        candidate, credential["token"], credential["token_id"]
                    )
                if check.get("verified"):
                    break
        post["meta_reconcile_attempts"] = (attempts + 1) if post.get("meta_reconcile_version") == 2 else 1
        post["meta_reconcile_version"] = 2
        post["meta_next_check_at"] = now_ts + (300 if meta_scheduled or attempts >= 5 else 60)
        if isinstance(check.get("meta_observation"), dict):
            from web.meta_diagnostics import diagnose
            post["meta_observation"] = check["meta_observation"]
            post["meta_diagnosis"] = diagnose(post)
        reconciled += 1
        if check.get("verified"):
            post["post_fb_id"] = check["video_id"]
            if check.get("fb_url"):
                post["fb_url"] = check["fb_url"]
            if meta_scheduled and check.get("status") == "scheduled":
                post.update({
                    "status": "meta_scheduled",
                    "meta_video_id": check["video_id"],
                    "meta_schedule_status": "scheduled",
                    "meta_schedule_verified_at": current_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "meta_scheduled_publish_time": check.get("publish_time") or post.get("meta_scheduled_publish_time"),
                    "outcome_unknown": False,
                    "error": "",
                })
                if post.get("first_comment") and post.get("first_comment_status") not in ("posted", "pending"):
                    try:
                        queued = enqueue_first_comment(
                            check["video_id"], credential["token"], post["first_comment"],
                            int(post["meta_scheduled_publish_time"]) + 30,
                            token_id=credential["token_id"], post_id=post.get("id"),
                        )
                        post["first_comment_status"] = "pending" if queued.get("success") else "queue_failed"
                        post["first_comment_queue_id"] = queued.get("queue_id") or ""
                    except Exception as exc:
                        post["first_comment_status"] = "queue_failed"
                        post["first_comment_error"] = sanitize_error(exc)
                continue
            # Ledger and post state must agree before displaying confirmed success.
            try:
                _record_posted_clip(post.get("media_file") or post.get("clip_filename"))
                post.update({"status": "published", "published_at": current_dt.strftime("%Y-%m-%d %H:%M:%S"), "meta_schedule_status": "published" if meta_scheduled else post.get("meta_schedule_status", ""), "error": ""})
            except Exception as exc:
                post["ledger_error"] = sanitize_error(exc)
            if post.get("first_comment") and post.get("first_comment_status") not in ("posted", "pending"):
                try:
                    queued = enqueue_first_comment(
                        check["video_id"], credential["token"], post["first_comment"],
                        int(now_ts) + 30, token_id=credential["token_id"], post_id=post.get("id"),
                    )
                    post["first_comment_status"] = "pending" if queued.get("success") else "queue_failed"
                except Exception as exc:
                    post["first_comment_status"] = "queue_failed"
                    post["first_comment_error"] = sanitize_error(exc)
        elif meta_scheduled and check.get("status") in ("error", "failed", "rejected", "schedule_mismatch"):
            post.update({
                "status": "failed", "meta_schedule_status": "rejected" if check.get("status") != "schedule_mismatch" else "schedule_mismatch",
                "retryable": False, "retry_stage": "meta_schedule_rejected",
                "error": "Meta did not confirm the requested scheduled state; inspect the Meta object before taking action.",
            })
        elif meta_scheduled and check.get("status") == "scheduled":
            post.update({
                "status": "meta_scheduled",
                "meta_schedule_status": "scheduled",
                "meta_schedule_verified_at": current_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "meta_next_check_at": max(now_ts + 300, float(post.get("meta_scheduled_publish_time") or now_ts) + 90),
            })
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
        if post.get("meta_upload_video_id"):
            post.update({"status": "processing", "retryable": False,
                         "retry_stage": "meta_processing", "outcome_unknown": True,
                         "meta_next_check_at": now_ts,
                         "error": "Upload đã có ID; đang đối soát Meta trước khi tiếp tục."})
        elif post.get("publish_started_at"):
            post.update({
                "status": "failed",
                "retryable": False,
                "retry_stage": "publish_outcome_unknown",
                "failed_at": current_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "error": "Worker dung sau khi bat dau publish; can doi soat Facebook truoc khi thu lai de tranh dang trung.",
            })
        else:
            post.update({
                "status": "scheduled",
                "retryable": True,
                "retry_stage": post.get("retry_stage") or "claim_recovery",
                "recovered_at": current_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "error": "Khoi phuc bai dang bi ket truoc khi bat dau publish (worker dung dot ngot)",
            })
        recovered += 1

    from multi_pc.publishing_settings import load_publishing_settings, credential_ready
    # Only schedules explicitly created in Meta mode request a handoff when
    # their Website and comment become ready. Existing app schedules stay put.
    from web.meta_handoff import handoff_eligibility, queue_handoffs
    for pending in posts:
        if pending.get("status") != "scheduled" or pending.get("requested_publish_mode") != "meta_scheduled":
            continue
        from multi_pc.meta_scheduling import parse_meta_schedule_time, MetaScheduleTimeError
        try:
            parse_meta_schedule_time(pending.get("scheduled_time"), now_ts=now_ts)
        except MetaScheduleTimeError as exc:
            pending.update({"status": "failed", "retryable": False,
                            "retry_stage": "meta_schedule_not_ready", "meta_schedule_status": "handoff_blocked",
                            "error": "Chưa giao được lịch cho Meta trong cửa sổ cho phép. Chọn giờ mới hoặc chế độ App giữ lịch. " + str(exc)})
            continue
        ok, reason = handoff_eligibility(pending, OUTPUT_DIR, now_ts=now_ts)
        if ok:
            result = queue_handoffs(posts, [str(pending["id"])], OUTPUT_DIR, token_vault, page_manager, now=current_dt)
            if result and not result[0].get("accepted"):
                pending["meta_handoff_error"] = result[0].get("reason", "")
        else:
            pending["meta_handoff_error"] = reason
    save_posts(posts)
    posting_threads = load_publishing_settings(POSTS_FILE.parent)["posting_threads"]
    selected_due = []
    def token_key(post):
        return str(post.get("token_id") or f"page:{post.get('page_id')}")
    reserved_tokens = {token_key(p) for p in posts if p.get("status") == "publishing"}
    reserved_pages = {str(p.get("page_id")) for p in posts if p.get("status") == "publishing"}
    candidates = list(posts)
    rate_blocked = 0
    for _ in range(len(posts)):
        if len(selected_due) >= posting_threads:
            break
        eligible = [p for p in candidates if token_key(p) not in reserved_tokens and str(p.get("page_id")) not in reserved_pages]
        due = next_paced_due_post(eligible, current_dt, global_seconds=0, token_seconds=900)
        if due is None:
            break
        token_id = str(due.get("token_id") or "")
        entry = token_vault.get_token_by_id(token_id) if token_id else None
        if entry and not credential_ready(entry):
            reserved_tokens.add(token_id)
            due["schedule_error"] = "Token đang cooldown hoặc Meta usage cao; app chờ quota, giữ nguyên token."
            rate_blocked += 1
            continue
        selected_due.append(due)
        reserved_tokens.add(token_key(due))
        reserved_pages.add(str(due.get("page_id")))
    claimed_posts = []
    for post in posts:
        if post.get("status") != "scheduled":
            continue
        # Content/CMS work is independent of Facebook. A delayed package must
        # never hold a due Meta post indefinitely; publish without its comment.
        scheduled_time = post.get("scheduled_time")
        if not scheduled_time:
            continue
        scheduled_dt = _parse_scheduled_time(scheduled_time)
        if scheduled_dt is None:
            post["schedule_error"] = "Thời gian lên lịch không hợp lệ"
            continue
        if scheduled_dt <= current_dt and any(post is selected for selected in selected_due):
            post["status"] = "publishing"
            post["claimed_at"] = current_dt.strftime("%Y-%m-%d %H:%M:%S")
            claimed_posts.append(post)

    if claimed_posts or recovered or rate_blocked:
        save_posts(posts)

    if claimed_posts:
        # Every thread owns a queue revision. Atomic field merges preserve both
        # independent publishes and concurrent Content Studio metadata updates.
        from concurrent.futures import ThreadPoolExecutor
        def publish_one(claim):
            local_posts = load_posts()
            local_post = next(row for row in local_posts if row.get("id") == claim.get("id"))
            with _active_posts_lock:
                _active_posts.add(local_post["id"])
            try:
                result = _publish_claimed_post(local_post, local_posts, poster, current_dt, token_vault, page_manager)
                save_posts(local_posts)
                return result
            finally:
                with _active_posts_lock:
                    _active_posts.discard(local_post["id"])
        with ThreadPoolExecutor(max_workers=posting_threads, thread_name_prefix="meta-publish") as pool:
            outcomes = list(pool.map(publish_one, claimed_posts))
        # Workers persisted their own revisions. Reload their merged results
        # before cleanup so a clip shared by parallel posts is retained until
        # every Page has a confirmed Meta result.
        posts = load_posts()

    removed = 0
    for published_post in posts:
        if published_post.get("status") == "published" and not published_post.get("local_video_deleted_at"):
            if remove_posted_clip_file(published_post.get("media_file") or published_post.get("clip_filename"), posts):
                published_post["local_video_deleted_at"] = current_dt.strftime("%Y-%m-%d %H:%M:%S")
                removed += 1
    if claimed_posts or recovered or reconciled or queue_result.get("changed") or removed:
        save_posts(posts)
    from web.meta_handoff import process_next_handoff
    # Processing is remote reconciliation, not an active local upload. Each
    # existing post keeps its duplicate fence; independent posts may proceed.
    reserved_tokens = {token_key(p) for p in posts if p.get("status") == "publishing"}
    reserved_pages = {str(p.get("page_id")) for p in posts if p.get("status") == "publishing"}
    handoffs = []
    for row in sorted((p for p in posts if p.get("status") == "meta_handoff"),
                      key=lambda p: (str(p.get("scheduled_time") or ""), str(p.get("id")))):
        key = token_key(row)
        pid = str(row.get("page_id"))
        if key in reserved_tokens or pid in reserved_pages:
            continue
        entry = token_vault.get_token_by_id(str(row.get("token_id") or ""))
        if entry and entry.get("status") == "ACTIVE" and not credential_ready(entry):
            continue
        # token_gap_seconds controls the actual publish timetable. Native
        # schedule handoffs can drain now; usage/cooldown and one active transfer
        # per token/Page in this batch still bound provider load.
        handoffs.append(row)
        reserved_tokens.add(key)
        reserved_pages.add(pid)
        if len(handoffs) >= posting_threads:
            break
    handed_off = 0
    if handoffs:
        from concurrent.futures import ThreadPoolExecutor
        def handoff_one(row):
            local_posts = load_posts()
            with _active_posts_lock:
                _active_posts.add(row["id"])
            try:
                return process_next_handoff(local_posts, save_posts, poster, OUTPUT_DIR, token_vault,
                                            page_manager, now=current_dt, post_id=row["id"])
            finally:
                with _active_posts_lock:
                    _active_posts.discard(row["id"])
        with ThreadPoolExecutor(max_workers=posting_threads, thread_name_prefix="meta-handoff") as pool:
            handed_off = sum(pool.map(handoff_one, handoffs))
        posts = load_posts()
    failed = sum(1 for post in outcomes if post.get("status") == "failed") if claimed_posts else 0
    return {"claimed": len(claimed_posts), "recovered": recovered, "failed": failed, "queue": queue_result,
            "handed_off": handed_off, "handoff_pending": any(p.get("status") == "meta_handoff" for p in posts), "posts": posts}



def _publish_claimed_post(post, posts, poster, current_dt, token_vault, page_manager):
    from src.content_packages import scheduled_video_path
    from src.publisher.meta_preflight import preflight_pages
    from src.publisher.first_comment_queue import enqueue_first_comment
    now_ts = current_dt.timestamp()
    post_id = post.get("id")
    page_id = post.get("page_id")
    clip_filename = post.get("media_file") or post.get("clip_filename")
    page_token = post.get("token")
    title = post.get("title", "")
    content = post.get("content", "")
    first_comment = str(post.get("first_comment") or "").strip()
    article_url = str(post.get("article_url") or "").strip()
    if article_url and article_url not in first_comment:
        first_comment = f"{first_comment}\n{article_url}".strip()
        post["first_comment"] = first_comment
    video_error = "Video file unavailable at publish time"
    try:
        video_path = scheduled_video_path(OUTPUT_DIR, clip_filename)
    except (ValueError, FileNotFoundError, OSError) as exc:
        video_path = None
        video_error = sanitize_error(exc)

    # Re-check the immutable Page/token binding at due time. The queue may
    # survive a token refresh/restart; never publish with a stale or generic
    # credential that was not verified for this exact page_id.
    page_record = next(
        (page for page in page_manager.list_pages() if str(page.get("page_id")) == str(page_id)),
        None,
    )
    # Legacy queue records may predate discovery-backed mappings. Preserve
    # their already-persisted page token for migration compatibility; new
    # schedules always have a token_id and must pass current preflight.
    # New queue records carry token_id and must pass current verified
    # Page/token preflight. Legacy records only carry their persisted exact
    # page token; preserve that compatibility for offline recovery and old
    # queues instead of letting an unrelated cached Page record block them.
    try:
        if post.get("token_id"):
            # Revalidate the exact token selected when the post was queued;
            # a later auto-rebalance must not silently switch credentials.
            bound_page = dict(page_record or {})
            bound_page["token_id"] = str(post.get("token_id") or "")
            verdict = preflight_pages([bound_page], token_vault, page_manager) if page_record else {"ok": False, "blocked": {"code": "missing_page", "stage": "mapping", "action": "Sync Page before publishing."}}
            blocked = verdict.get("blocked") or {}
            verified = verdict["ready"][0] if verdict.get("ok") else None
        else:
            blocked = {}
            verified = {"token": page_token, "token_id": post.get("token_id", "")} if page_token else None
    except Exception as exc:
        post.update({"status": "failed", "retryable": True,
                     "retry_stage": "meta_preflight",
                     "error": sanitize_error(exc)})
        save_posts(posts)
        return post
    if verified is None:
        post.update({
            "status": "failed",
            "retryable": True,
            "retry_stage": "meta_preflight",
            "error": blocked.get("action") or "Page credential mapping is not verified; Sync Page before publishing.",
            "meta_preflight": {
                "stage": blocked.get("stage"),
                "code": blocked.get("code"),
                "action": blocked.get("action"),
                "reconnect_required": True,
            },
        })
        return post
    post["token"] = verified["token"]
    post["token_id"] = verified["token_id"]
    page_token = verified["token"]

    if not video_path or not video_path.exists():
        post.update({
            "status": "failed",
            "error": video_error,
            "retryable": True,
            "retry_stage": "local_video",
        })
        return post

    if post.get("auto_first_comment") or post.get("type") == "reel":
        url = str(post.get("article_url") or "").strip()
        comment = str(post.get("first_comment") or "").strip()
        website_ready = post.get("website_status") in (None, "", "ready")
        if not (url and website_ready and url in comment):
            post["status"] = "failed" if post.get("website_status") == "failed" else "scheduled"
            post["retryable"] = post["status"] == "failed"
            post["retry_stage"] = "website_content"
            post["schedule_error"] = "Đang chờ bài Website và First Comment chứa link; chưa gửi Reel lên Meta."
            post.pop("claimed_at", None)
            return post
        post.pop("schedule_error", None)

    # Website creation belongs to schedule confirmation. Due-time publishing
    # only consumes persisted article_url/first_comment and must never create
    # a duplicate CMS article. A prior CMS failure does not cancel Facebook.
    if first_comment:
        post["first_comment_status"] = "ready"
    elif post.get("auto_first_comment") and post.get("content_package_status") in ("queued", "running"):
        post["first_comment_status"] = "pending_generation"
    else:
        post["first_comment_status"] = post.get("first_comment_status") or "not_configured"

    try:
        # The worker publishes first, then comments. Passing an empty comment
        # prevents MetaReelPoster from making an implicit/out-of-order call.
        post["publish_started_at"] = current_dt.strftime("%Y-%m-%d %H:%M:%S")
        save_posts(posts)
        def persist_upload(video_id):
            post.update({"meta_upload_video_id": str(video_id), "outcome_unknown": True})
            save_posts(posts)
        result = poster.publish_reel(
            page_id=page_id,
            page_token=page_token,
            video_path=str(video_path),
            description=f"{title}\n\n{content}",
            first_comment="",
            token_id=post.get("token_id"),
            reconcile_seconds=12,
            on_upload_initialized=persist_upload,
        )
        facebook_id = result.get("video_id") or result.get("reel_id")
        if (result.get("processing") or result.get("outcome_unknown") or (not result.get("success") and post.get("meta_upload_video_id"))) and (result.get("meta_post_id") or result.get("upload_video_id") or post.get("meta_upload_video_id")):
            post.update({"status": "processing", "meta_post_id": str(result.get("meta_post_id") or ""),
                         "meta_upload_video_id": str(result.get("upload_video_id") or post.get("meta_upload_video_id") or ""),
                         "meta_reconcile_attempts": 0, "meta_next_check_at": now_ts + 60,
                         "retryable": False, "retry_stage": "meta_processing",
                         "meta_publish_error": sanitize_error(result.get("error")),
                         "meta_publish_error_code": result.get("code") or "",
                         "outcome_unknown": bool(result.get("outcome_unknown")),
                         "error": "Meta is processing; awaiting independent read-only verification. Do not retry."})
            save_posts(posts)
            return post
        if not result.get("success") or not facebook_id:
            post.update({
                "status": "failed",
                "retryable": not (result.get("outcome_unknown") or (result.get("success") and not facebook_id)),
                "retry_stage": "facebook_publish",
                "error": result.get("error", "Lỗi Meta Graph API không xác định"),
            })
            return post

        post.update({
            "status": "published",
            "post_fb_id": facebook_id,
            "fb_url": result.get("fb_url") or (f"https://www.facebook.com/reel/{facebook_id}" if facebook_id else ""),
            "published_at": current_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "error": "",
            "retryable": False,
            "outcome_unknown": False,
        })

        # Persist the Meta object id before optional local/comment side effects.
        # A comment or ledger failure must never turn a confirmed Reel into a
        # failed Reel that an operator could inadvertently publish twice.
        save_posts(posts)
        try:
            _record_posted_clip(clip_filename)
        except Exception as exc:
            post["ledger_error"] = sanitize_error(exc)
        if first_comment:
            try:
                comment_result = poster.post_first_comment(facebook_id, page_token, first_comment)
                if comment_result.get("success"):
                    post["comment_id"] = comment_result.get("comment_id")
                    post["first_comment_status"] = "posted"
                    post["first_comment_error"] = ""
                else:
                    queued = enqueue_first_comment(
                        facebook_id, page_token, first_comment,
                        int(current_dt.timestamp()) + 30,
                        token_id=post.get("token_id"), post_id=post_id,
                        outcome_unknown=bool(comment_result.get("outcome_unknown")),
                    )
                    post["first_comment_status"] = "verification_pending" if queued.get("outcome_unknown") else ("pending_retry" if queued.get("success") else "queue_failed")
                    if queued.get("outcome_unknown"):
                        post["first_comment_error"] = "First Comment outcome unknown; queue is paused until Meta verification."
                    post["first_comment_error"] = comment_result.get("error", "Không thể đăng First Comment")
                    post["first_comment_queue_id"] = queued.get("queue_id")
            except Exception as exc:
                try:
                    queued = enqueue_first_comment(
                        facebook_id, page_token, first_comment,
                        int(current_dt.timestamp()) + 30,
                        token_id=post.get("token_id"), post_id=post_id,
                        outcome_unknown=True,
                    )
                    post["first_comment_status"] = "verification_pending" if queued.get("success") else "queue_failed"
                    post["first_comment_queue_id"] = queued.get("queue_id")
                except Exception:
                    post["first_comment_status"] = "queue_failed"
                post["first_comment_error"] = sanitize_error(exc)
    except Exception:
        post.update({
            "status": "failed",
            "retryable": False,
            "retry_stage": "publish_outcome_unknown",
            "error": "Publish started but outcome is unknown; reconcile on Facebook before retrying.",
        })

    return post

def process_scheduled_posts_once(*args, **kwargs):
    """Serialize worker/manual cycles so one due record cannot publish twice."""
    if not _cycle_lock.acquire(blocking=False):
        return {"claimed": 0, "recovered": 0, "failed": 0, "busy": True, "posts": []}
    try:
        return _process_scheduled_posts_once(*args, **kwargs)
    finally:
        _cycle_lock.release()


# Prevent two processes (reloader + packaged waitress) from running the publishing
# loop at the same time and double-claiming due posts.
_PROCESS_LEASE = ProcessLease("scheduled-publisher", BASE_DIR / "data", stale_after=180)


def scheduled_publisher_worker_loop():
    """Run publishing cycles continuously; all external calls remain in the cycle helper."""
    global _worker_started, _worker_waiting_for_lease
    _worker_waiting_for_lease = True
    while not _PROCESS_LEASE.acquire():
        time.sleep(5)
    _worker_waiting_for_lease = False
    if not _worker_lock.acquire(blocking=False):
        _PROCESS_LEASE.release()
        _safe_log("[ScheduledPublisher] Worker loop already running in this process; skipping duplicate start.")
        return
    _worker_started = True
    with _heartbeat_lock:
        _heartbeat["started_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _safe_log("[ScheduledPublisher] Background publisher worker started with Idempotent Claim Lock!")
    try:
        while True:
            _PROCESS_LEASE.touch()
            result = {}
            try:
                result = process_scheduled_posts_once()
                if result.get("busy"):
                    # A manual run-due or a previous long cycle still holds the lock;
                    # do not touch the heartbeat or it would mask the real cycle result.
                    pass
                else:
                    _touch_heartbeat(True)
                    if result.get("claimed") or result.get("recovered"):
                        _safe_log(f"[ScheduledPublisher] cycle claimed={result.get('claimed')} recovered={result.get('recovered')} failed={result.get('failed')}")
            except Exception as exc:
                _touch_heartbeat(False, exc)
                _safe_log(f"[ScheduledPublisher] Loop Error: {sanitize_error(exc)}")
            time.sleep(1 if result.get("handoff_pending") else CYCLE_INTERVAL_SECONDS)
    finally:
        _worker_started = False
        with _heartbeat_lock:
            _heartbeat["running"] = False
        _worker_lock.release()
        _PROCESS_LEASE.release()


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
_worker_thread_lock = threading.Lock()


def start_worker_thread(restart_dead=False):
    """Idempotently start the background worker; safe to call from app and packaged entrypoint.

    The guard must survive a thread that exits immediately (a stubbed loop in tests
    or a lease-losing duplicate start): callers still observe one stable handle
    instead of spawning a new thread per call.
    """
    global _worker_thread
    with _worker_thread_lock:
        if _worker_thread is not None:
            if _worker_thread.is_alive() or not restart_dead:
                return _worker_thread
        thread = threading.Thread(target=scheduled_publisher_worker_loop, daemon=True, name="scheduled-publisher")
        _worker_thread = thread
        thread.start()
        return thread
