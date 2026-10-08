"""Move existing app-held schedules to Meta without creating another post."""
from datetime import datetime
from urllib.parse import urlparse
from pathlib import Path
import threading

from multi_pc.meta_scheduling import MetaScheduleTimeError, parse_meta_schedule_time
from src.content_packages import scheduled_video_path
from src.publisher.meta_preflight import preflight_pages
from src.english_text import assert_english


def _handoff_eligibility(post, output_dir, *, now_ts=None, verify_text=True):
    if post.get("local_archived_at"):
        return False, "Bài đã được xóa khỏi danh sách app."
    if post.get("status") != "scheduled" or post.get("publish_mode") == "meta_scheduled":
        return False, "Chỉ chuyển bài đang do app giữ lịch."
    if any(post.get(key) for key in ("meta_video_id", "meta_upload_video_id", "meta_post_id", "post_fb_id", "publish_started_at", "outcome_unknown")):
        return False, "Bài đã gửi lên Meta; cần đối soát trước."
    if verify_text:
        try:
            for key in ("title", "content", "first_comment", "first_comment_snapshot"):
                assert_english(post.get(key, ""), key)
        except ValueError:
            return False, "Nội dung phải là tiếng Anh. Sửa Content Studio trước khi giao lịch Meta."
    try:
        parse_meta_schedule_time(post.get("scheduled_time"), now_ts=now_ts)
    except MetaScheduleTimeError as exc:
        reasons = {"meta_schedule_too_soon": "Còn dưới hoặc đúng 10 phút: app sẽ đăng theo lịch.",
                   "meta_schedule_too_far": "Chỉ giao Meta khi lịch nằm trong 29 ngày tới."}
        return False, reasons.get(exc.code, "Thời gian lên lịch không hợp lệ.")
    url = str(post.get("article_url") or post.get("website_url") or "").strip()
    comment = str(post.get("first_comment_snapshot") or post.get("first_comment") or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or post.get("website_status") not in (None, "", "ready"):
        return False, "Chờ bài Website sẵn sàng."
    if not comment or comment.count(url) != 1:
        return False, "Chờ First Comment chứa đúng một link Website."
    if not post.get("token_id"):
        return False, "Thiếu credential đã gắn với lịch; cần Sync Page."
    if post.get("output_pipeline") and not (post.get("website_video_status") == "verified" or
            (post.get("website_media_mode") == "youtube" and post.get("website_video_status") == "youtube_embed_verified")):
        return False, "Chờ bài Website có video gốc đầy đủ và player đã xác minh."
    try:
        path = scheduled_video_path(output_dir, post.get("media_file") or post.get("clip_filename"))
        from src.media_quality_gate import require_publishable
        require_publishable(path, post)
        from src.video_recovery_media import verify_recovery_digest
        verify_recovery_digest(post, path)
    except (ValueError, FileNotFoundError, OSError) as exc:
        return False, str(exc) or "Không tìm thấy video local."
    return True, ""


_DISPLAY_CACHE = {}
_DISPLAY_CACHE_LOCK = threading.RLock()


def _display_cache_key(post, output_dir, now_ts):
    media = str(post.get("media_file") or post.get("clip_filename") or "")
    signature = None
    if media:
        try:
            path = Path(output_dir) / Path(media).name
            stat = path.stat()
            signature = (stat.st_size, stat.st_mtime_ns)
        except OSError:
            signature = (None, None)
    return (str(post.get("id") or ""), str(post.get("status") or ""),
            str(post.get("publish_mode") or ""), str(post.get("scheduled_time") or ""),
            str(post.get("article_url") or post.get("website_url") or ""),
            str(post.get("website_status") or ""),
            str(post.get("first_comment_snapshot") or post.get("first_comment") or ""),
            str(post.get("token_id") or ""), media, signature,
            int(float(now_ts or datetime.now().timestamp()) // 60))


def handoff_eligibility(post, output_dir, *, now_ts=None, verify_text=True):
    """Return local handoff readiness without making a Graph request.

    Paginated table reads use a short-lived advisory cache and skip the
    expensive language model. The handoff API keeps verify_text=True and
    repeats the complete validation immediately before any Meta request.
    """
    if verify_text:
        return _handoff_eligibility(post, output_dir, now_ts=now_ts, verify_text=True)
    key = _display_cache_key(post, output_dir, now_ts)
    with _DISPLAY_CACHE_LOCK:
        cached = _DISPLAY_CACHE.get(key)
    if cached is not None:
        return cached
    result = _handoff_eligibility(post, output_dir, now_ts=now_ts, verify_text=False)
    with _DISPLAY_CACHE_LOCK:
        _DISPLAY_CACHE[key] = result
        if len(_DISPLAY_CACHE) > 1024:
            for old_key in list(_DISPLAY_CACHE)[:256]:
                _DISPLAY_CACHE.pop(old_key, None)
    return result


def queue_handoffs(posts, post_ids, output_dir, vault, pages, *, now=None):
    """Called under the publisher cycle lock; no Graph uploads occur here."""
    current = now or datetime.now()
    by_id = {str(post.get("id")): post for post in posts}
    page_records = {str(page.get("page_id")): page for page in pages.list_pages()}
    results = []
    for post_id in dict.fromkeys(post_ids):
        post = by_id.get(post_id)
        if post and post.get("status") in ("meta_handoff", "meta_scheduled"):
            results.append({"post_id": post_id, "accepted": False, "already_queued": True,
                            "reason": "Bài đã ở hàng chờ giao Meta hoặc đã được Meta nhận."})
            continue
        ok, reason = handoff_eligibility(post or {}, output_dir, now_ts=current.timestamp())
        if ok:
            page = page_records.get(str(post.get("page_id")))
            verdict = preflight_pages([{**page, "token_id": post["token_id"]}], vault, pages) if page else {"ok": False}
            ok = bool(verdict.get("ok"))
            reason = "Credential gốc chưa được xác minh cho Page; hãy Sync Page." if not ok else ""
        if ok:
            post.update({"status": "meta_handoff", "publish_mode": "meta_scheduled",
                         "meta_schedule_status": "handoff_queued",
                         "meta_handoff_requested_at": current.strftime("%Y-%m-%d %H:%M:%S"),
                         "meta_handoff_error": "", "retryable": False})
        results.append({"post_id": post_id, "accepted": ok, "reason": reason})
    return results


def process_next_handoff(posts, save, poster, output_dir, vault, pages, *, now=None, post_id=None):
    """Persist one selected handoff before sending any Meta request."""
    current = now or datetime.now()
    waiting = sorted((post for post in posts if post.get("status") == "meta_handoff" and not post.get("local_archived_at")
                      and (post_id is None or str(post.get("id")) == str(post_id))),
                     key=lambda post: (str(post.get("scheduled_time") or ""), str(post.get("id"))))
    if not waiting:
        return 0
    post = waiting[0]
    candidate = {**post, "status": "scheduled", "publish_mode": "app_queue"}
    ok, reason = handoff_eligibility(candidate, output_dir, now_ts=current.timestamp())
    page = next((page for page in pages.list_pages() if str(page.get("page_id")) == str(post.get("page_id"))), None)
    verdict = preflight_pages([{**page, "token_id": post["token_id"]}], vault, pages, refresh=True) if ok and page else {"ok": False}
    if not ok or not verdict.get("ok"):
        post.update({"status": "scheduled", "publish_mode": "app_queue",
                     "meta_schedule_status": "handoff_blocked", "meta_handoff_error": reason or "Credential gốc chưa được xác minh; hãy Sync Page."})
        save(posts)
        return 1
    credential = verdict["ready"][0]
    publish_at = parse_meta_schedule_time(post["scheduled_time"], now_ts=current.timestamp())
    comment = str(post.get("first_comment_snapshot") or post.get("first_comment") or "").strip()
    post["content_frozen_at"] = post.get("content_frozen_at") or current.isoformat(timespec="seconds")
    post["first_comment_snapshot"] = comment
    post.update({"status": "processing", "meta_schedule_status": "upload_started",
                 "meta_scheduled_publish_time": publish_at, "outcome_unknown": True,
                 "meta_handoff_started_at": current.strftime("%Y-%m-%d %H:%M:%S"),
                 "meta_next_check_at": current.timestamp() + 60,
                 "retry_stage": "meta_schedule_verification", "retryable": False,
                 "error": "Đang gửi video và lịch lên Meta; chờ xác minh."})
    save(posts)

    def initialized(video_id):
        post.update({"meta_video_id": str(video_id), "meta_upload_video_id": str(video_id),
                     "meta_schedule_status": "upload_initialized"})
        save(posts)

    # A crash/exception after upload starts leaves processing + outcome_unknown.
    # The existing worker reconciles the stored object; it never re-uploads it.
    result = poster.publish_reel(
        page_id=post["page_id"], page_token=credential["token"],
        video_path=str(scheduled_video_path(output_dir, post.get("media_file") or post.get("clip_filename"))),
        description=f"{post.get('title', '')}\n\n{post.get('content', '')}".strip(),
        first_comment=comment, schedule_time=publish_at, token_id=post["token_id"],
        post_id=post["id"], on_upload_initialized=initialized,
    )
    if result.get("meta_attempt"):
        post["meta_publish_attempt"] = result["meta_attempt"]
    from web.scheduled_publisher import sanitize_error
    video_id = str(result.get("meta_video_id") or result.get("upload_video_id") or post.get("meta_video_id") or "")
    if result.get("success") and result.get("status") == "SCHEDULED" and video_id:
        comment_result = result.get("comment_result") or {}
        post.update({"status": "meta_scheduled", "meta_video_id": video_id,
                     "meta_upload_video_id": video_id, "meta_schedule_status": "scheduled",
                     "meta_schedule_verified_at": result.get("meta_schedule_verified_at") or current.strftime("%Y-%m-%d %H:%M:%S"),
                     "meta_next_check_at": max(current.timestamp() + 300, publish_at + 90),
                     "outcome_unknown": False, "error": "",
                     "first_comment_status": "pending" if comment_result.get("success") else "queue_failed",
                     "first_comment_queue_id": comment_result.get("queue_id") or ""})
    elif video_id or result.get("outcome_unknown") or result.get("processing"):
        post.update({"meta_video_id": video_id, "meta_upload_video_id": video_id,
                     "meta_schedule_status": result.get("meta_schedule_status") or "verification_pending",
                     "meta_finish_not_sent": bool(result.get("finish_not_sent")),
                     "outcome_unknown": bool(result.get("outcome_unknown", True)),
                     "meta_publish_error": sanitize_error(result.get("error")),
                     "error": sanitize_error(result.get("error") or "Chờ đối soát lịch trên Meta.")})
    elif result.get("code") == "invalid_media":
        post.update({"status": "failed", "meta_schedule_status": "handoff_blocked",
                     "retry_stage": "invalid_media", "publish_error_code": "invalid_media",
                     "retryable": False, "outcome_unknown": False,
                     "error": sanitize_error(result.get("error"))})
    else:
        # A definitive pre-upload failure leaves the original app schedule intact.
        post.update({"status": "scheduled", "publish_mode": "app_queue",
                     "meta_schedule_status": "handoff_blocked", "outcome_unknown": False, "error": "",
                     "meta_handoff_error": sanitize_error(result.get("error") or "Meta chưa nhận lịch; app tiếp tục giữ lịch.")})
        # A later app publish may itself need reconciliation; it must not be
        # mistaken for a native schedule from this rejected handoff.
        for key in ("meta_scheduled_publish_time", "meta_next_check_at", "retry_stage"):
            post.pop(key, None)
    save(posts)
    return 1
