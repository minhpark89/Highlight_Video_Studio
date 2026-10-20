"""Resolve interrupted attempts without discarding an unknown Meta outcome."""
from datetime import datetime
import re
from urllib.parse import parse_qs, urlsplit

import requests

from src.publisher.meta_api import bearer_headers
from web.meta_diagnostics import safe_error
from web.meta_reconcile_policy import existing_object, timestamp


def needs_operator_resolution(post):
    return bool(post.get("status") == "failed" and not existing_object(post)
                and not post.get("post_fb_id") and not post.get("reel_id")
                and not post.get("local_archived_at") and not post.get("meta_cancel_requested")
                and (post.get("outcome_unknown") or post.get("retry_stage") == "publish_outcome_unknown"))


def video_identifier(value):
    value = str(value or "").strip()
    if re.fullmatch(r"\d+", value):
        return value
    parsed = urlsplit(value)
    if parsed.scheme != "https" or parsed.hostname not in ("www.facebook.com", "facebook.com", "m.facebook.com"):
        raise ValueError("Dán ID video hoặc liên kết Reel/video trên facebook.com.")
    match = re.search(r"/(?:reel|videos)/(\d+)/?$", parsed.path)
    identifier = match.group(1) if match else (parse_qs(parsed.query).get("v") or [""])[0]
    if not re.fullmatch(r"\d+", identifier):
        raise ValueError("Liên kết chưa có ID video. Mở video trên Page rồi sao chép liên kết đầy đủ.")
    return identifier


def read_owned_video(poster, post, mapping, value):
    video_id = video_identifier(value)
    response = requests.get(
        f"{poster.base_url}/{video_id}", headers=bearer_headers(mapping["page_token"]),
        params={"fields": "id,from,status,permalink_url,description,created_time"}, timeout=15,
    )
    data = response.json()
    if not response.ok or not isinstance(data, dict) or data.get("error"):
        raise ValueError(safe_error((data.get("error") or {}).get("message") if isinstance(data, dict) else "Không đọc được video Meta."))
    owner = data.get("from") or {}
    if str(data.get("id")) != video_id or str(owner.get("id")) != str(post.get("page_id")):
        raise ValueError("Meta chưa xác nhận video thuộc đúng Page của bài này.")
    return data


def find_candidates(poster, post, mapping):
    """A limited search helps the operator; an empty search never proves absence."""
    expected = " ".join(f"{post.get('title', '')}\n\n{post.get('content', '')}".split())
    if not expected:
        return []
    started = timestamp(post.get("publish_started_at") or post.get("scheduled_time"))
    params = {"fields": "id,description,created_time,permalink_url", "limit": 50}
    if started:
        params.update(since=int(started - 7200), until=int(started + 86400))
    matches = []
    for _ in range(3):
        response = requests.get(
            f"{poster.base_url}/{post['page_id']}/videos",
            headers=bearer_headers(mapping["page_token"]), params=params, timeout=15,
        )
        data = response.json()
        if not response.ok or not isinstance(data, dict) or data.get("error"):
            raise ValueError(safe_error((data.get("error") or {}).get("message") if isinstance(data, dict) else "Không đọc được danh sách video."))
        for video in data.get("data") or []:
            if " ".join(str(video.get("description") or "").split()) == expected:
                video_id = str(video.get("id") or "")
                if re.fullmatch(r"\d+", video_id):
                    matches.append({"video_id": video_id, "created_time": video.get("created_time"),
                                    "url": poster.public_video_permalink(video.get("permalink_url"), video_id)})
        paging = data.get("paging") or {}
        after = (paging.get("cursors") or {}).get("after")
        if not paging.get("next") or not after:
            break
        params["after"] = after
    return matches


def attach_existing(post, posts, data):
    if not needs_operator_resolution(post):
        raise ValueError("Bài đã thay đổi trạng thái; tải lại trước khi đối soát.")
    video_id = str(data["id"])
    for other in posts:
        if other.get("id") != post.get("id") and video_id in (
                existing_object(other), str(other.get("post_fb_id") or ""), str(other.get("reel_id") or "")):
            raise ValueError("Video đã gắn với bài khác trong app. Mở bài hiện có để kiểm tra.")
    from web.meta_diagnostics import observation
    post.setdefault("publish_resolution_history", []).append({
        "at": datetime.now().astimezone().isoformat(), "action": "link_existing", "video_id": video_id,
    })
    post.update(status="processing", meta_upload_video_id=video_id, meta_video_id=video_id,
                meta_observation=observation(data, 200), meta_next_check_at=0,
                retryable=False, outcome_unknown=True, retry_stage="meta_processing",
                error="Đã gắn video đúng Page. App đang tự xác minh trạng thái đăng.")


def return_to_draft(post, confirmation):
    if not needs_operator_resolution(post):
        raise ValueError("Bài đã có Meta ID hoặc đã đổi trạng thái; kiểm tra lại.")
    if confirmation is not True:
        raise ValueError("Cần kiểm tra cả video, bài đã đăng và lịch chờ trên Page trước khi xác nhận chưa có bài.")
    post.setdefault("publish_resolution_history", []).append({
        "at": datetime.now().astimezone().isoformat(), "action": "operator_confirmed_absent",
        "previous_error": post.get("error"), "publish_started_at": post.get("publish_started_at"),
        "previous_schedule": post.get("scheduled_time"),
    })
    for key in ("publish_started_at", "claimed_at", "content_frozen_at", "approved_at", "first_comment_snapshot",
                "meta_scheduled_publish_time", "meta_next_check_at", "next_retry_at"):
        post.pop(key, None)
    post.update(status="draft", approval_mode="manual", retryable=False, outcome_unknown=False,
                retry_stage="", error="", schedule_error="Đã đối soát thủ công. Chọn giờ mới và duyệt Draft để đăng lại.")
