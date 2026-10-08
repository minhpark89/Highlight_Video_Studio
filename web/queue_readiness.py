"""Local reasons a schedule cannot run, shared by the worker and its views."""
from datetime import datetime


def credential_block(entry):
    if not entry:
        return "token_missing", "Không tìm thấy Token đã gắn với bài. Mở Quản lý Token để kiểm tra."
    if entry.get("status") != "ACTIVE":
        detail = str(entry.get("error_msg") or entry.get("page_access_error") or "").strip()
        message = "Token chưa hoạt động; xác minh lại Token và đồng bộ đúng Page."
        if "API access blocked" in detail:
            message = "Meta chặn quyền truy cập của Token (API access blocked). Cần khôi phục quyền rồi Sync Page."
        return "token_invalid", message
    from multi_pc.publishing_settings import credential_ready
    if not credential_ready(entry):
        return "token_cooldown", "Token đang giới hạn lượt gọi Meta; app giữ lịch và chờ quota phục hồi."
    return "", ""


def schedule_readiness(post, tokens, *, now=None):
    """Explain local gates without a Graph request or changing the queue."""
    now = now or datetime.now()
    result = {"actionable": False, "blocked_code": "", "blocked_reason": "", "action": ""}
    if post.get("status") not in ("scheduled", "meta_handoff"):
        return result
    if post.get("media_quality_error"):
        return {**result, "blocked_code": "media_quality", "action": "video",
                "blocked_reason": post["media_quality_error"]}
    if post.get("local_archived_at") or post.get("meta_cancel_requested"):
        return {**result, "blocked_code": "cancelled", "blocked_reason": "Bài đã dừng hoặc xóa khỏi app."}
    token_id = str(post.get("meta_recovery_token_id") or post.get("token_id") or "")
    if token_id:
        code, reason = credential_block(tokens.get(token_id))
        if code:
            return {**result, "blocked_code": code, "blocked_reason": reason,
                    "action": "tokens", "token_id": token_id}
    try:
        retry_at = float(post.get("next_retry_at") or 0)
    except (TypeError, ValueError):
        retry_at = 0
    if retry_at > now.timestamp():
        return {**result, "blocked_code": "retry_backoff", "retry_at": retry_at,
                "blocked_reason": "Đang chờ thời điểm thử lại đã định."}
    if post.get("auto_first_comment") or post.get("type") == "reel":
        url = str(post.get("article_url") or "").strip()
        comment = str(post.get("first_comment_snapshot") or post.get("first_comment") or "")
        if not url or post.get("website_status") not in (None, "", "ready"):
            return {**result, "blocked_code": "website", "action": "content",
                    "blocked_reason": "Đang chờ Website sẵn sàng; kiểm tra Content của bài."}
        if comment.count(url) != 1:
            return {**result, "blocked_code": "comment", "action": "content",
                    "blocked_reason": "First Comment cần đúng một link Website của bài."}
    return {**result, "actionable": True}
