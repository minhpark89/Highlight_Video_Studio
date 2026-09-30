import os
import time
import requests
from pathlib import Path
from datetime import datetime

class MetaReelPoster:
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

    def publish_reel(self, page_id, page_token, video_path, description="", first_comment="", schedule_time=None, token_id=None):
        video_path = Path(video_path)
        if not video_path.exists():
            return {"success": False, "error": f"Video không tồn tại: {video_path}"}

        file_size = video_path.stat().st_size
        track_target = token_id or page_token
        finish_started = False

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
                err_msg = init_data.get("error", {}).get("message", str(init_data))
                return {"success": False, "error": f"Meta init rejected (HTTP {r_init.status_code}): {err_msg}"}
            if "video_id" not in init_data:
                err_msg = init_data.get("error", {}).get("message", str(init_data))
                return {"success": False, "error": f"Lỗi khởi tạo upload: {err_msg}"}

            video_id = init_data["video_id"]
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
                target_ts = None
                if isinstance(schedule_time, (int, float)):
                    target_ts = int(schedule_time)
                else:
                    try:
                        s_str = str(schedule_time).strip().replace("T", " ")
                        if len(s_str) == 16:
                            s_str += ":00"
                        dt = datetime.strptime(s_str[:19], "%Y-%m-%d %H:%M:%S")
                        target_ts = int(dt.timestamp())
                    except Exception:
                        pass

                if target_ts:
                    now_ts = int(time.time())
                    if target_ts < now_ts + 600:
                        target_ts = now_ts + 660
                    
                    finish_payload["video_state"] = "SCHEDULED"
                    finish_payload["scheduled_publish_time"] = target_ts
                    is_scheduled = True
                else:
                    finish_payload["video_state"] = "PUBLISHED"
            else:
                finish_payload["video_state"] = "PUBLISHED"

            finish_started = True
            r_finish = requests.post(finish_url, data=finish_payload, timeout=35)
            self._track_headers(track_target, r_finish)
            try:
                finish_data = r_finish.json()
            except ValueError:
                return {"success": False, "outcome_unknown": True, "error": f"Meta finish non-JSON response (HTTP {r_finish.status_code}); reconcile before retry"}
            if not r_finish.ok:
                err_msg = finish_data.get("error", {}).get("message", str(finish_data))
                return {"success": False, "outcome_unknown": True, "error": f"Meta finish rejected (HTTP {r_finish.status_code}); reconcile before retry: {err_msg}"}
            # A success response without an object id is not authoritative.
            if not finish_data.get("video_id") and not finish_data.get("reel_id"):
                err_msg = finish_data.get("error", {}).get("message", str(finish_data))
                return {"success": False, "outcome_unknown": True, "error": f"Meta finish returned no object id; outcome is unknown: {err_msg}"}

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
                        token_id=track_target,
                    )
                except Exception:
                    comment_result = {"success": False, "error": "First comment queue failed after Reel finish; do not republish the Reel"}

            return {
                "success": True,
                "video_id": finish_data.get("video_id") or finish_data.get("reel_id") or video_id,
                "fb_url": finish_data.get("permalink_url") or f"https://www.facebook.com/reel/{video_id}",
                "status": "SCHEDULED" if is_scheduled else "PUBLISHED",
                "scheduled_publish_time": finish_payload.get("scheduled_publish_time"),
                "comment_result": comment_result
            }

        except Exception as e:
            if finish_started:
                return {"success": False, "outcome_unknown": True, "error": "Meta finish request failed; outcome unknown, reconcile before retry"}
            return {"success": False, "error": f"Ngoại lệ khi đăng/lên lịch Reel: {str(e)}"}

    def post_first_comment(self, object_id, page_token, comment_text, token_id=None):
        """Bắn First Comment vào Reel hoặc Post"""
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
            return {"success": False, "error": str(e)}
