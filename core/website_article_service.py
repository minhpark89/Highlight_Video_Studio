"""Portable client for the BestNews-compatible CMS.

The old application imported this client from a separate installation on D:\\.
Keeping it here makes website publishing work on every machine that installs HVS.
"""

from __future__ import annotations

import json
import mimetypes
import os
import re
import shlex
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urljoin, urlparse

import requests


class WebsiteServiceError(RuntimeError):
    """Raised when CMS authentication, upload, or publishing is not verified."""


@dataclass
class WebsiteConfig:
    base_url: str
    username: str
    password: str
    login_url: str = ""
    api_base_url: str = ""
    timeout: int = 30
    video_upload: Dict[str, Any] = None

    @classmethod
    def from_file(cls, config_path: str) -> "WebsiteConfig":
        path = Path(config_path)
        if not path.exists():
            raise WebsiteServiceError(f"Không tìm thấy cấu hình website: {path}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise WebsiteServiceError(f"Cấu hình website không hợp lệ: {exc}") from exc

        base_url = str(raw.get("base_url") or "").strip().rstrip("/")
        username = str(raw.get("username") or "").strip()
        password = str(raw.get("password") or "")
        if not base_url.startswith(("http://", "https://")):
            raise WebsiteServiceError("Website URL phải bắt đầu bằng http:// hoặc https://")
        if not username or not password:
            raise WebsiteServiceError("Thiếu username hoặc password của CMS")
        return cls(
            base_url=base_url,
            username=username,
            password=password,
            login_url=str(raw.get("login_url") or f"{base_url}/login"),
            api_base_url=str(raw.get("api_base_url") or f"{base_url}/admin/api/v1").rstrip("/"),
            timeout=max(5, int(raw.get("timeout") or 30)),
            video_upload=dict(raw.get("video_upload") or {}),
        )


class _BackendSession:
    def __init__(self, cfg: WebsiteConfig):
        self.cfg = cfg
        self.http = requests.Session()
        self.http.headers.update({
            "Accept": "application/json",
            "User-Agent": "HighlightVideoStudio/1.0",
            "X-Requested-With": "XMLHttpRequest",
        })
        self.csrf_token = ""
        self.authenticated = False

    @staticmethod
    def _csrf_from_html(html: str) -> str:
        patterns = (
            r'<meta\s+name=["\']csrf-token["\']\s+content=["\']([^"\']+)',
            r'name=["\']_token["\']\s+value=["\']([^"\']+)',
        )
        for pattern in patterns:
            match = re.search(pattern, html or "", re.IGNORECASE)
            if match:
                return match.group(1)
        return ""

    def login(self) -> None:
        page = self.http.get(self.cfg.login_url, timeout=self.cfg.timeout)
        page.raise_for_status()
        token = self._csrf_from_html(page.text)
        if not token:
            raise WebsiteServiceError("CMS không trả CSRF token tại trang đăng nhập")

        response = self.http.post(
            self.cfg.login_url,
            data={
                "_token": token,
                "email": self.cfg.username,
                "username": self.cfg.username,
                "password": self.cfg.password,
            },
            allow_redirects=True,
            timeout=self.cfg.timeout,
        )
        response.raise_for_status()
        if "/login" in urlparse(response.url).path.lower():
            raise WebsiteServiceError("CMS từ chối username/password")

        dashboard = self.http.get(f"{self.cfg.base_url}/admin/dashboard", timeout=self.cfg.timeout)
        dashboard.raise_for_status()
        self.csrf_token = self._csrf_from_html(dashboard.text)
        if not self.csrf_token:
            raise WebsiteServiceError("Đăng nhập CMS thành công nhưng thiếu CSRF token quản trị")
        self.http.headers["X-CSRF-TOKEN"] = self.csrf_token
        self.authenticated = True


class WebsiteArticleService:
    def __init__(self, config_path: str):
        self.config_path = str(config_path)
        self.cfg = WebsiteConfig.from_file(config_path)

    def _ensure_session(self, session: _BackendSession) -> None:
        if not session.authenticated:
            session.login()

    @staticmethod
    def _response_payload(response: requests.Response) -> Dict[str, Any]:
        try:
            payload = response.json()
        except Exception as exc:
            raise WebsiteServiceError(
                f"CMS trả dữ liệu không phải JSON (HTTP {response.status_code})"
            ) from exc
        if response.status_code >= 400:
            message = payload.get("message") or payload.get("error") or str(payload)
            raise WebsiteServiceError(f"CMS HTTP {response.status_code}: {message}")
        return payload

    def test_connection(self) -> Dict[str, Any]:
        session = _BackendSession(self.cfg)
        self._ensure_session(session)
        response = session.http.get(
            f"{self.cfg.api_base_url}/posts",
            params={"per_page": 1},
            timeout=self.cfg.timeout,
        )
        payload = self._response_payload(response)
        return {
            "success": True,
            "authenticated": True,
            "posts_api": response.status_code == 200,
            "api_base_url": self.cfg.api_base_url,
            "message": "Đăng nhập CMS và đọc Posts API thành công",
            "response_ok": bool(payload.get("ok", True)),
        }

    def _presign_and_upload(self, session: _BackendSession, file_path: str) -> str:
        self._ensure_session(session)
        path = Path(file_path)
        if not path.is_file():
            raise WebsiteServiceError(f"Không tìm thấy file cần upload: {path}")

        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        is_video = content_type.startswith("video/")
        generic_endpoint = f"{self.cfg.api_base_url}/uploads/presigned-image-url"
        generic_request = {
            "fileName": path.name,
            "contentType": content_type,
            "size": path.stat().st_size,
            "auditContext": {
                "record_type": "HighlightVideoStudio",
                "action_label": "publish article asset",
            },
        }

        # Website article media always uses the CMS' generic uploader. The
        # Social Planner endpoint belongs to a separately licensed feature and
        # must not be part of the default Website publishing path.
        presign = session.http.post(
            generic_endpoint,
            json=generic_request,
            timeout=self.cfg.timeout,
        )

        payload = self._response_payload(presign)
        data = payload.get("data") or payload
        upload_data = data.get("upload") or {}
        upload = {
            "url": data.get("upload_url") or upload_data.get("url"),
            "method": data.get("method") or upload_data.get("method") or "PUT",
            "headers": data.get("headers") or upload_data.get("headers") or {},
        }
        public_url = (
            data.get("public_url")
            or data.get("fileUrl")
            or data.get("file_url")
        )

        upload_url = upload.get("url")
        if not upload_url or not public_url:
            raise WebsiteServiceError("CMS không trả upload URL/public URL hợp lệ")

        upload_headers = {
            str(key): str(value)
            for key, value in (upload.get("headers") or {}).items()
            if str(key).lower() != "content-length"
        }
        if not any(key.lower() == "content-type" for key in upload_headers):
            upload_headers["Content-Type"] = content_type

        method = str(upload.get("method") or "PUT").upper()
        with path.open("rb") as handle:
            uploaded = requests.request(
                method,
                upload_url,
                headers=upload_headers,
                data=handle,
                timeout=max(self.cfg.timeout, 300),
            )
        if uploaded.status_code not in (200, 201, 204):
            raise WebsiteServiceError(
                f"Upload CDN thất bại: HTTP {uploaded.status_code} {uploaded.text[:200]}"
            )

        self.verify_public_media(public_url, require_range=is_video)
        return str(public_url)

    def upload_public_media(self, file_path: str) -> str:
        session = _BackendSession(self.cfg)
        return self._presign_and_upload(session, file_path)

    def _video_settings(self) -> Dict[str, Any]:
        raw = dict(self.cfg.video_upload or {})
        method = str(raw.get("method") or "cms").strip().lower()
        # preview.5/6 shipped an empty SCP placeholder. Treat only that empty
        # legacy placeholder as CMS-native upload; preserve real SCP configs.
        if method == "scp" and not any(str(raw.get(key) or "").strip() for key in (
            "host", "username", "private_key_path", "remote_dir", "public_base_url",
        )):
            method = "cms"
        return {
            "method": method,
            "host": str(raw.get("host") or "").strip(),
            "port": int(raw.get("port") or 22),
            "username": str(raw.get("username") or "").strip(),
            "private_key_path": os.path.expandvars(str(raw.get("private_key_path") or "").strip()),
            "remote_dir": str(raw.get("remote_dir") or "").strip().rstrip("/"),
            "public_base_url": str(raw.get("public_base_url") or "").strip().rstrip("/"),
        }

    @staticmethod
    def _required_executable(name: str) -> str:
        executable = shutil.which(name)
        if not executable:
            raise WebsiteServiceError(
                f"Không tìm thấy {name}. Windows cần cài OpenSSH Client để upload video."
            )
        return executable

    def _validate_scp_settings(self) -> Dict[str, Any]:
        settings = self._video_settings()
        missing = [
            key for key in ("host", "username", "private_key_path", "remote_dir", "public_base_url")
            if not settings[key]
        ]
        if missing:
            raise WebsiteServiceError("Thiếu cấu hình video SCP: " + ", ".join(missing))
        key_path = Path(settings["private_key_path"])
        if not key_path.is_file():
            raise WebsiteServiceError(f"Không tìm thấy SSH private key: {key_path}")
        if not settings["public_base_url"].startswith("https://"):
            raise WebsiteServiceError("Public video base URL phải dùng HTTPS")
        return settings

    def test_video_uploader(self) -> Dict[str, Any]:
        settings = self._video_settings()
        if settings["method"] == "cms":
            return {
                "success": True,
                "method": "cms",
                "message": "CMS upload đã chọn; quyền upload sẽ được xác minh khi gửi file.",
            }
        if settings["method"] != "scp":
            raise WebsiteServiceError("Video upload method chỉ hỗ trợ cms hoặc scp")
        settings = self._validate_scp_settings()
        ssh = self._required_executable("ssh")
        remote_test = f"test -d {shlex.quote(settings['remote_dir'])} && test -w {shlex.quote(settings['remote_dir'])}"
        command = [
            ssh, "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new",
            "-o", f"ConnectTimeout={min(self.cfg.timeout, 20)}", "-p", str(settings["port"]),
            "-i", settings["private_key_path"], f"{settings['username']}@{settings['host']}", remote_test,
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=self.cfg.timeout + 10)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "SSH bị từ chối").strip()[-500:]
            raise WebsiteServiceError(f"Không thể ghi vào thư mục video qua SSH: {detail}")
        return {
            "success": True,
            "method": "scp",
            "message": "SSH hợp lệ và thư mục video cho phép ghi.",
            "host": settings["host"],
            "remote_dir": settings["remote_dir"],
        }

    def upload_video(self, file_path: str) -> str:
        path = Path(file_path)
        if not path.is_file():
            raise WebsiteServiceError(f"Không tìm thấy video cần upload: {path}")
        settings = self._video_settings()
        if settings["method"] == "cms":
            return self.upload_public_media(str(path))
        if settings["method"] != "scp":
            raise WebsiteServiceError("Video upload method chỉ hỗ trợ cms hoặc scp")

        settings = self._validate_scp_settings()
        scp = self._required_executable("scp")
        safe_stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", path.stem).strip("-")[:60] or "video"
        suffix = path.suffix.lower() if path.suffix else ".mp4"
        remote_name = f"{safe_stem}-{uuid.uuid4().hex[:10]}{suffix}"
        remote_path = f"{settings['remote_dir']}/{remote_name}"
        command = [
            scp, "-q", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new",
            "-o", f"ConnectTimeout={min(self.cfg.timeout, 20)}", "-P", str(settings["port"]),
            "-i", settings["private_key_path"], str(path),
            f"{settings['username']}@{settings['host']}:{shlex.quote(remote_path)}",
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=max(self.cfg.timeout, 600))
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "SCP thất bại").strip()[-500:]
            raise WebsiteServiceError(f"Upload video qua SCP thất bại: {detail}")
        public_url = f"{settings['public_base_url']}/{remote_name}"
        self.verify_public_media(public_url, require_range=True)
        return public_url

    def verify_public_media(self, url: str, require_range: bool = False) -> Dict[str, Any]:
        if not str(url).startswith("https://"):
            raise WebsiteServiceError("Media công khai phải dùng HTTPS")
        response = requests.head(str(url), allow_redirects=True, timeout=self.cfg.timeout)
        if response.status_code != 200:
            raise WebsiteServiceError(f"Media public chưa truy cập được: HTTP {response.status_code}")
        content_type = str(response.headers.get("Content-Type") or "").lower()
        if require_range:
            ranged = requests.get(
                str(url),
                headers={"Range": "bytes=0-1023"},
                stream=True,
                timeout=self.cfg.timeout,
            )
            try:
                if ranged.status_code != 206:
                    raise WebsiteServiceError(
                        f"Video server không hỗ trợ tua/Range (HTTP {ranged.status_code})"
                    )
                if "video/" not in str(ranged.headers.get("Content-Type") or content_type).lower():
                    raise WebsiteServiceError("Public URL không trả Content-Type video")
            finally:
                ranged.close()
        return {
            "success": True,
            "url": str(response.url),
            "content_type": content_type,
            "accept_ranges": response.headers.get("Accept-Ranges", ""),
        }

    def verify_article(self, article_url: str, attempts: int = 4) -> Dict[str, Any]:
        expected_path = urlparse(article_url).path.rstrip("/")
        last_error = ""
        for attempt in range(attempts):
            try:
                response = requests.get(article_url, allow_redirects=True, timeout=self.cfg.timeout)
                final_path = urlparse(response.url).path.rstrip("/")
                if response.status_code == 200 and final_path == expected_path:
                    return {"success": True, "status_code": 200, "url": response.url}
                last_error = f"HTTP {response.status_code}, final URL {response.url}"
            except requests.RequestException as exc:
                last_error = str(exc)
            if attempt + 1 < attempts:
                time.sleep(1.5)
        raise WebsiteServiceError(f"Không xác minh được bài viết public: {last_error}")

    def publish_article(
        self,
        title: str,
        slug: str,
        body_html: str,
        image_path: Optional[str] = None,
        image_url: str = "",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        clean_title = str(title or "").strip()
        clean_slug = re.sub(r"[^a-z0-9-]+", "-", str(slug or "").lower()).strip("-")
        if not clean_title or not clean_slug or not str(body_html or "").strip():
            raise WebsiteServiceError("Thiếu title, slug hoặc nội dung bài viết")

        session = _BackendSession(self.cfg)
        self._ensure_session(session)
        final_image_url = str(image_url or "").strip()
        if image_path:
            final_image_url = self._presign_and_upload(session, image_path)

        article_url = f"{self.cfg.base_url}/blog/{clean_slug}"
        request_data = {
            "title": clean_title,
            "slug": clean_slug,
            "description": str(body_html),
            "image": final_image_url or None,
            "seo_title": clean_title[:255],
            "seo_description": re.sub(r"<[^>]+>", " ", str(body_html))[:300],
            "og_title": clean_title[:255],
            "og_image": final_image_url or None,
            "twitter_title": clean_title[:255],
            "twitter_image": final_image_url or None,
            "is_active": True,
            "is_home": True,
            "is_top": False,
            "category_ids": [],
            "tag_ids": [],
        }
        if dry_run:
            return {
                "status": "dry_run",
                "article_url": article_url,
                "payload": request_data,
            }

        response = session.http.post(
            f"{self.cfg.api_base_url}/posts",
            json=request_data,
            timeout=max(self.cfg.timeout, 60),
        )
        payload = self._response_payload(response)
        if not payload.get("ok", True):
            raise WebsiteServiceError(str(payload.get("message") or "CMS không xác nhận tạo bài"))

        created = payload.get("data") or {}
        returned_slug = created.get("slug") if isinstance(created, dict) else None
        if returned_slug:
            article_url = f"{self.cfg.base_url}/blog/{returned_slug}"
        self.verify_article(article_url)
        return {
            "status": "success",
            "article_url": article_url,
            "post_id": created.get("id") if isinstance(created, dict) else None,
            "image_url": final_image_url,
        }
