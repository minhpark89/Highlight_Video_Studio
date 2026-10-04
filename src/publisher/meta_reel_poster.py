import os
import time
import requests
import re
from src.english_text import assert_english
from pathlib import Path
from datetime import datetime

class MetaReelPoster:
    @staticmethod
    def _meta_error(data):
        error = data.get("error") if isinstance(data, dict) else None
        if not isinstance(error, dict):
            return "Meta did not return an error object"
        details = [str(error.get("message") or "Meta rejected the request")]
        for key, label in (("code", "code"), ("error_subcode", "subcode"),
                           ("error_user_title", "title"), ("error_user_msg", "detail"),
                           ("fbtrace_id", "trace")):
            if error.get(key):
                details.append(f"{label}: {error[key]}")
        return " | ".join(details)

    def __init__(self, api_version="v22.0", token_vault=None):
        self.api_version = api_version
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        self.token_vault = token_vault

    def _track_headers(self, token_or_id, response):
        if self.token_vault and response is not None:
            try:
                self.token_vault.record_usage(token_or_id, response.headers)
            except Exception:
                pass

    def check_processing_reel(self, candidate_id, page_token, token_id=None):
        """Read only: a finish post_id is a candidate, never proof of publication."""
        if not re.fullmatch(r"[0-9]+(?:_[0-9]+)?", str(candidate_id or "")) or not page_token:
            return {"verified": False}
        try:
            response = requests.get(f"{self.base_url}/{candidate_id}", params={
                "fields": "id,status,permalink_url", "access_token": page_token,
            }, timeout=12)
            self._track_headers(token_id or page_token, response)
            from web.meta_diagnostics import observation
            data = response.json()
            seen = observation(data, response.status_code)
            seen["error"] = seen["error"].replace(page_token, "[redacted]")
            if not response.ok:
                return {"verified": False, "meta_observation": seen}
            status = data.get("status") or {}
            state = str(status.get("video_status") or "").lower() if isinstance(status, dict) else ""
            # An explicit ready/published state and a real permalink are needed;
            # a bare id, processing state or error is not evidence of a live Reel.
            publishing = status.get("publishing_phase") or {} if isinstance(status, dict) else {}
            published = str(publishing.get("publish_status") or "").lower() == "published"
            permalink = str(data.get("permalink_url") or "").strip()
            if permalink.startswith("/reel/"):
                permalink = "https://www.facebook.com" + permalink
            if (str(data.get("id")) == str(candidate_id) and state in ("ready", "published")
                    and published and permalink.startswith("https://www.facebook.com/reel/")):
                return {"verified": True, "video_id": str(candidate_id), "fb_url": permalink, "meta_observation": seen}
            return {"verified": False, "meta_observation": seen}
        except (requests.RequestException, ValueError, TypeError):
            pass
        return {"verified": False}

    def inspect_reel(self, video_id, page_token, token_id=None):
        """Read one existing object and expose only diagnostic fields."""
        from web.meta_diagnostics import observation
        if not re.fullmatch(r"[0-9]+", str(video_id or "")) or not page_token:
            return observation({"error": {"message": "Thiếu Meta upload ID hoặc Token gốc."}}, 400)
        try:
            response = requests.get(f"{self.base_url}/{video_id}", params={
                "fields": "id,status,permalink_url", "access_token": page_token,
            }, timeout=15)
            self._track_headers(token_id or page_token, response)
            seen = observation(response.json(), response.status_code)
            seen["error"] = seen["error"].replace(page_token, "[redacted]")
            return seen
        except (requests.RequestException, ValueError, TypeError):
            return observation({"error": {"message": "Không đọc được trạng thái Meta; hãy kiểm tra lại."}}, 503)

    def finish_existing_reel(self, page_id, page_token, video_id, description, *, schedule_time=None, token_id=None):
        """Finish an existing upload only; never initialize or transfer another video."""
        from web.meta_diagnostics import safe_error
        try:
            assert_english(description, "Reel description")
        except ValueError as exc:
            return {"accepted": False, "state": "rejected", "error": str(exc)}
        if not re.fullmatch(r"[0-9]+", str(video_id or "")):
            return {"accepted": False, "state": "rejected", "error": "Meta upload ID không hợp lệ."}
        payload = {"upload_phase": "finish", "access_token": page_token, "video_id": str(video_id),
                   "description": description, "video_state": "PUBLISHED"}
        if schedule_time is not None:
            from multi_pc.meta_scheduling import parse_meta_schedule_time
            payload.update(video_state="SCHEDULED", scheduled_publish_time=parse_meta_schedule_time(schedule_time))
        try:
            response = requests.post(f"{self.base_url}/{page_id}/video_reels", data=payload, timeout=35)
            self._track_headers(token_id or page_token, response)
            data = response.json()
            if response.status_code >= 500 or not isinstance(data, dict):
                return {"accepted": False, "state": "unknown", "error": "Chưa xác nhận phản hồi Finish; tiếp tục đối soát đúng Meta ID."}
            if not response.ok or data.get("error") or data.get("success") is False:
                return {"accepted": False, "state": "rejected", "error": safe_error(self._meta_error(data)).replace(page_token, "[redacted]")}
            if data.get("success") is not True and not any(data.get(key) for key in ("video_id", "reel_id", "post_id")):
                return {"accepted": False, "state": "unknown", "error": "Meta chưa xác nhận Finish; tiếp tục đối soát đúng Meta ID."}
            return {"accepted": True, "state": "accepted", "error": ""}
        except (requests.RequestException, ValueError, TypeError):
            return {"accepted": False, "state": "unknown", "error": "Phản hồi Finish chưa rõ; không gửi lại tự động."}

    def check_scheduled_reel(self, candidate_id, page_token, expected_publish_time=None, token_id=None):
        """Read the Reel object and retain phase evidence even before acceptance."""
        from web.meta_diagnostics import observation
        if not re.fullmatch(r"[0-9]+(?:_[0-9]+)?", str(candidate_id or "")) or not page_token:
            return {"verified": False, "status": "unverified"}
        try:
            response = requests.get(f"{self.base_url}/{candidate_id}", params={
                "fields": "id,status,permalink_url", "access_token": page_token,
            }, timeout=12)
            self._track_headers(token_id or page_token, response)
            data = response.json()
            seen = observation(data, response.status_code)
            seen["error"] = seen["error"].replace(page_token, "[redacted]")
            result = {"verified": False, "status": "unverified", "meta_observation": seen}
            if not response.ok or not isinstance(data, dict) or str(data.get("id") or "") != str(candidate_id):
                return result
            publish_state = seen["publishing_status"]
            try:
                raw_time = seen["publish_time"]
                try:
                    publish_time = int(raw_time or 0)
                except (TypeError, ValueError):
                    parsed = datetime.fromisoformat(str(raw_time).replace("Z", "+00:00"))
                    if parsed.tzinfo is None:
                        raise ValueError("Meta schedule lacks a timezone")
                    publish_time = int(parsed.timestamp())
            except (TypeError, ValueError):
                publish_time = 0
            if publish_state == "scheduled" and publish_time:
                if expected_publish_time is not None and abs(publish_time - int(expected_publish_time)) > 60:
                    return {**result, "status": "schedule_mismatch", "publish_time": publish_time}
                return {**result, "verified": True, "status": "scheduled", "publish_time": publish_time,
                        "video_id": str(data["id"]), "fb_url": str(data.get("permalink_url") or "")}
            if publish_state == "published":
                public_check = self.check_processing_reel(candidate_id, page_token, token_id)
                return {**result, **public_check, "status": "published", "publish_time": publish_time}
            if publish_state in ("error", "failed", "rejected"):
                return {**result, "status": publish_state,
                        "publish_time": publish_time, "video_id": str(data["id"])}
            return result
        except (requests.RequestException, ValueError, TypeError):
            return {"verified": False, "status": "unverified", "meta_observation": observation({}, 503)}

    def publish_reel(self, page_id, page_token, video_path, description="", first_comment="", schedule_time=None, token_id=None, reconcile_seconds=0, post_id=None, on_upload_initialized=None):
        try:
            assert_english(description, "Reel description")
            assert_english(first_comment, "First Comment")
        except ValueError as exc:
            return {"success": False, "retryable": False, "error": str(exc), "code": "non_english_content"}
        video_path = Path(video_path)
        if not video_path.exists():
            return {"success": False, "error": f"Video không tồn tại: {video_path}"}

        file_size = video_path.stat().st_size
        track_target = token_id or page_token
        finish_started = False
        target_ts = None
        video_id = ""
        if schedule_time is not None:
            from multi_pc.meta_scheduling import parse_meta_schedule_time
            try:
                target_ts = parse_meta_schedule_time(schedule_time)
            except ValueError as exc:
                return {"success": False, "error": str(exc), "code": getattr(exc, "code", "invalid_schedule_time")}

        # Bước 1: Khởi tạo phiên upload Reel (Initialize)
        init_url = f"{self.base_url}/{page_id}/video_reels"
        init_payload = {
            "upload_phase": "start",
            "access_token": page_token
        }
        try:
            r_init = requests.post(init_url, data=init_payload, timeout=25)
            self._track_headers(track_target, r_init)
            try:
                init_data = r_init.json()
            except ValueError:
                return {"success": False, "error": f"Meta init non-JSON response (HTTP {r_init.status_code})"}
            if not r_init.ok:
                err_msg = self._meta_error(init_data)
                return {"success": False, "error": f"Meta init rejected (HTTP {r_init.status_code}): {err_msg}"}
            if "video_id" not in init_data:
                err_msg = self._meta_error(init_data)
                return {"success": False, "error": f"Lỗi khởi tạo upload: {err_msg}"}

            video_id = init_data["video_id"]
            if on_upload_initialized is not None:
                try:
                    on_upload_initialized(str(video_id))
                except Exception:
                    return {"success": False, "processing": True, "outcome_unknown": True,
                            "upload_video_id": str(video_id), "meta_video_id": str(video_id),
                            "meta_scheduled_publish_time": target_ts,
                            "meta_schedule_status": "persistence_failed",
                            "error": "Upload initialized but local handoff could not be persisted; reconcile before retry."}
            upload_url = init_data.get("upload_url", f"https://rupload.facebook.com/video-upload/{self.api_version}/{video_id}")

            # Bước 2: Upload Binary Video (Transfer phase)
            headers = {
                "Authorization": f"OAuth {page_token}",
                "offset": "0",
                "file_size": str(file_size),
                "Content-Type": "application/octet-stream"
            }
            with open(video_path, "rb") as f:
                r_upload = requests.post(upload_url, headers=headers, data=f, timeout=300)
            
            if r_upload.status_code not in [200, 201]:
                return {"success": False, "error": f"Lỗi upload binary video (status {r_upload.status_code}): {r_upload.text}"}

            # Bước 3: Xuất bản Reel hoặc Lên lịch (Finish phase)
            finish_url = f"{self.base_url}/{page_id}/video_reels"
            finish_payload = {
                "upload_phase": "finish",
                "access_token": page_token,
                "video_id": video_id,
                "description": description
            }

            is_scheduled = False
            if schedule_time:
                from multi_pc.meta_scheduling import parse_meta_schedule_time
                try:
                    target_ts = parse_meta_schedule_time(schedule_time)
                except ValueError as exc:
                    return {"success": False, "processing": True, "outcome_unknown": False,
                            "upload_video_id": str(video_id), "meta_video_id": str(video_id),
                            "meta_scheduled_publish_time": target_ts, "meta_schedule_status": "schedule_expired",
                            "code": getattr(exc, "code", "invalid_schedule_time"),
                            "retryable": False, "finish_not_sent": True,
                            "error": "Video upload completed, but the Meta scheduling window expired before Finish. Choose a new time for this existing upload."}
                finish_payload["video_state"] = "SCHEDULED"
                finish_payload["scheduled_publish_time"] = target_ts
                is_scheduled = True
            else:
                finish_payload["video_state"] = "PUBLISHED"

            finish_started = True
            r_finish = requests.post(finish_url, data=finish_payload, timeout=35)
            self._track_headers(track_target, r_finish)
            try:
                finish_data = r_finish.json()
            except ValueError:
                return {"success": False, "processing": True, "outcome_unknown": True,
                        "upload_video_id": str(video_id), "meta_video_id": str(video_id),
                        "meta_scheduled_publish_time": target_ts, "meta_schedule_status": "verification_pending",
                        "error": f"Meta finish non-JSON response (HTTP {r_finish.status_code}); reconcile before retry"}
            if not isinstance(finish_data, dict):
                raise ValueError("Meta finish response is not an object")
            if r_finish.status_code >= 500:
                raise RuntimeError("Meta finish server failure; reconcile before retry")
            if not r_finish.ok or finish_data.get("error") or finish_data.get("success") is False:
                err_msg = self._meta_error(finish_data)
                return {"success": False, "outcome_unknown": False, "code": "meta_finish_rejected",
                        "retryable": True,
                        "error": f"Meta finish rejected (HTTP {r_finish.status_code}): {err_msg}"}
            if is_scheduled:
                meta_id = str(finish_data.get("video_id") or finish_data.get("reel_id") or video_id)
                check = self.check_scheduled_reel(meta_id, page_token, target_ts, token_id=track_target)
                if not check.get("verified"):
                    state = str(check.get("status") or "unverified")
                    return {"success": False, "processing": True, "outcome_unknown": True,
                            "meta_post_id": str(finish_data.get("post_id") or ""),
                            "upload_video_id": str(video_id), "meta_video_id": meta_id,
                            "meta_scheduled_publish_time": target_ts,
                            "meta_schedule_status": state,
                            "error": "Meta finish was accepted but the scheduled state is not independently verified; reconcile before retry."}
            # A successful Finish response is an acceptance, not proof that the
            # Reel is public. Verify the upload video object with a read-only GET.
            if not is_scheduled and reconcile_seconds:
                deadline = time.time() + max(0, min(int(reconcile_seconds), 30))
                while True:
                    check = self.check_processing_reel(video_id, page_token, token_id=track_target)
                    if check.get("verified"):
                        comment_result = (self.post_first_comment(video_id, page_token, first_comment.strip(), token_id=track_target)
                                          if first_comment and first_comment.strip() else None)
                        return {"success": True, "video_id": check["video_id"], "fb_url": check["fb_url"],
                                "status": "PUBLISHED", "comment_result": comment_result, "verified_meta": True}
                    if time.time() >= deadline:
                        break
                    time.sleep(min(2, max(0, deadline - time.time())))
                return {"success": False, "processing": True, "outcome_unknown": True,
                        "meta_post_id": str(finish_data.get("post_id") or ""), "upload_video_id": str(video_id),
                        "error": "Meta accepted finish; Reel processing. Verify remotely before marking posted; do not retry."}
            if not is_scheduled and finish_data.get("post_id") and not finish_data.get("video_id") and not finish_data.get("reel_id"):
                return {"success": False, "processing": True, "outcome_unknown": True,
                        "meta_post_id": str(finish_data["post_id"]), "upload_video_id": str(video_id),
                        "error": "Meta accepted finish; Reel processing. Verify remotely before marking posted; do not retry."}
            # A success response without an object id is not authoritative.
            if not is_scheduled and not finish_data.get("video_id") and not finish_data.get("reel_id"):
                err_msg = self._meta_error(finish_data)
                return {"success": False, "processing": True, "outcome_unknown": True,
                        "upload_video_id": str(video_id), "meta_video_id": str(video_id),
                        "error": f"Meta finish returned no object id; outcome is unknown: {err_msg}"}

            # Bước 4: Tự động bắn First Comment nếu đăng ngay
            comment_result = None
            if not is_scheduled and first_comment and first_comment.strip():
                try:
                    time.sleep(3)
                    comment_result = self.post_first_comment(video_id, page_token, first_comment.strip(), token_id=track_target)
                except Exception:
                    comment_result = {"success": False, "error": "First comment failed after Reel publish; do not republish the Reel"}
            elif is_scheduled and first_comment and first_comment.strip():
                try:
                    from src.publisher.first_comment_queue import enqueue_first_comment
                    comment_result = enqueue_first_comment(
                        video_id, page_token, first_comment.strip(),
                        int(finish_payload["scheduled_publish_time"]) + 30,
                        token_id=track_target, post_id=post_id,
                    )
                except Exception:
                    comment_result = {"success": False, "error": "First comment queue failed after Reel finish; do not republish the Reel"}

            return {
                "success": True,
                "video_id": finish_data.get("video_id") or finish_data.get("reel_id") or video_id,
                "fb_url": finish_data.get("permalink_url") or f"https://www.facebook.com/reel/{video_id}",
                "status": "SCHEDULED" if is_scheduled else "PUBLISHED",
                "scheduled_publish_time": finish_payload.get("scheduled_publish_time"),
                "meta_video_id": str(finish_data.get("video_id") or finish_data.get("reel_id") or video_id) if is_scheduled else "",
                "meta_schedule_status": "scheduled" if is_scheduled else "",
                "meta_schedule_verified_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S") if is_scheduled else "",
                "comment_result": comment_result
            }

        except Exception as e:
            if finish_started:
                return {"success": False, "processing": True, "outcome_unknown": True,
                        "upload_video_id": str(video_id), "meta_video_id": str(video_id),
                        "meta_scheduled_publish_time": target_ts, "meta_schedule_status": "verification_pending",
                        "error": "Meta finish request failed; outcome unknown, reconcile before retry"}
            return {"success": False, "error": f"Ngoại lệ khi đăng/lên lịch Reel: {str(e)}"}

    def post_first_comment(self, object_id, page_token, comment_text, token_id=None):
        """Bắn First Comment vào Reel hoặc Post"""
        try:
            assert_english(comment_text, "First Comment")
        except ValueError as exc:
            return {"success": False, "error": str(exc)}
        url = f"{self.base_url}/{object_id}/comments"
        payload = {
            "message": comment_text,
            "access_token": page_token
        }
        try:
            r = requests.post(url, data=payload, timeout=15)
            if self.token_vault:
                self._track_headers(token_id or page_token, r)
            data = r.json()
            if "id" in data:
                return {"success": True, "comment_id": data["id"]}
            return {"success": False, "error": data.get("error", {}).get("message", str(data))}
        except Exception as e:
            return {"success": False, "outcome_unknown": True,
                    "error": "First Comment response was not confirmed; verify on Meta before retrying."}
