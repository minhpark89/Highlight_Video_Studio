"""Describe observed Meta phases without guessing a lost historical Finish response."""
import re
from datetime import datetime


def safe_error(value):
    text = str(value or "")
    text = re.sub(r"(?i)(access_token|page_token|authorization|api_key|password|token)[=:\s]+[^\s&\"',]+", r"\1=[redacted]", text)
    text = re.sub(r"EAA[A-Za-z0-9]{15,}", "[redacted]", text)
    return " ".join(text.split())[:500]


def observation(data, http_status=None):
    data = data if isinstance(data, dict) else {}
    status = data.get("status") if isinstance(data.get("status"), dict) else {}
    def phase(key):
        value = status.get(key) or {}
        return value if isinstance(value, dict) else {}
    error = data.get("error") if isinstance(data.get("error"), dict) else {}
    uploading = phase("uploading_phase")
    publishing = phase("publishing_phase")
    return {"checked_at": datetime.now().astimezone().isoformat(),
            "http_status": http_status if isinstance(http_status, int) else None,
            "id": str(data.get("id") or ""), "video_status": str(status.get("video_status") or "").lower(),
            "uploading_status": str(uploading.get("status") or "").lower(),
            "bytes_transferred": uploading.get("bytes_transferred") if isinstance(uploading.get("bytes_transferred"), (int, float)) else None,
            "processing_status": str(phase("processing_phase").get("status") or "").lower(),
            "publishing_status": str(publishing.get("publish_status") or publishing.get("status") or "").lower(),
            "publish_time": publishing.get("publish_time") or status.get("publish_time"),
            "permalink_url": str(data.get("permalink_url") or ""),
            "copyright_matches": phase("copyright_check_status").get("matches_found"),
            "error_code": error.get("code"), "error_subcode": error.get("error_subcode"),
            "error": safe_error(error.get("error_user_msg") or error.get("message"))}


def diagnose(post, seen=None):
    seen = seen or post.get("meta_observation") or {}
    upload_id = str(post.get("meta_upload_video_id") or "")
    result = {"state": "unverified", "message": "Chờ xác minh trạng thái trên Meta",
              "detail": "Bấm Kiểm tra Meta để đọc trạng thái hiện tại.", "can_finish_existing": False,
              "can_reschedule_existing": False,
              "video_id": upload_id or str(post.get("meta_video_id") or post.get("meta_post_id") or "")}
    if not seen:
        return result
    if seen.get("error_code") or seen.get("http_status") not in (None, 200):
        result.update(state="meta_error", message="Không đọc được đối tượng Meta",
                      detail=seen.get("error") or "Kiểm tra quyền của Token gốc và đối tượng trong Meta Business Suite.")
        return result
    publishing = seen.get("publishing_status")
    processing = seen.get("processing_status")
    if publishing == "published":
        result.update(state="published", message="Meta báo đã đăng", detail="Worker sẽ xác minh permalink trước khi cập nhật lịch sử và First Comment.")
    elif publishing == "scheduled":
        result.update(state="scheduled", message="Meta đang giữ lịch", detail="Meta đã nhận lịch đăng của video này.")
    elif seen.get("video_status") == "upload_complete" and processing == "not_started" and publishing == "not_started":
        known_error = post.get("meta_publish_error")
        result.update(state="finish_pending", message="Upload đã đủ; Meta chưa xử lý hoặc đăng",
                      detail=("Phản hồi lần đăng trước: " + safe_error(known_error)) if known_error else
                      "Bản cũ không lưu phản hồi Finish chi tiết, nên chưa xác định được bước Finish bị từ chối hay Meta chưa xử lý yêu cầu. Có thể gửi Finish một lần cho đúng video đã upload.")
        result["can_finish_existing"] = bool(seen.get("http_status") == 200 and not seen.get("error") and
            post.get("status") == "processing" and upload_id and
            seen.get("id") == upload_id and seen.get("uploading_status") == "complete" and
            post.get("token_id") and not post.get("meta_finish_recovery_attempts") and not seen.get("copyright_matches"))
        if post.get("publish_mode") == "meta_scheduled" or post.get("meta_scheduled_publish_time"):
            from multi_pc.meta_scheduling import parse_meta_schedule_time
            try:
                parse_meta_schedule_time(post.get("meta_scheduled_publish_time") or post.get("scheduled_time"))
            except (ValueError, TypeError):
                result.update(can_reschedule_existing=result["can_finish_existing"], can_finish_existing=False,
                              detail="Video đã upload đủ nhưng giờ Meta hết cửa sổ hợp lệ. Chọn giờ mới để hoàn tất đúng ID này; không cần upload lại.")
        if post.get("meta_finish_recovery_attempts"):
            result["detail"] = "Đã gửi một yêu cầu hoàn tất cho video này; tiếp tục đối soát trước khi có thao tác khác. " + safe_error(post.get("meta_finish_recovery_error"))
    elif "error" in (publishing, processing, seen.get("video_status")) or "failed" in (publishing, processing):
        result.update(state="rejected", message="Meta báo lỗi xử lý video", detail=seen.get("error") or "Xem video trong Meta Business Suite để kiểm tra định dạng, quyền và bản quyền.")
    elif processing in ("in_progress", "processing") or publishing in ("in_progress", "processing"):
        result.update(state="processing", message="Meta đang xử lý video", detail="Giữ Meta ID hiện có và chờ đối soát; không tạo upload mới.")
    else:
        result.update(message="Meta chưa xác nhận xuất bản", detail="Trạng thái video: " + (seen.get("video_status") or "chưa có") + "; tiếp tục kiểm tra đối tượng hiện có.")
    return result
