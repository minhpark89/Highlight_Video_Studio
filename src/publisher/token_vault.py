import os
import json
import base64
import time
import requests
import uuid
from pathlib import Path
from datetime import datetime
from multi_pc.json_io import replace_with_retry

class TokenVault:
    def __init__(self, data_dir=r"D:\Highlight_Video_Studio"):
        self.data_dir = Path(data_dir)
        self.vault_file = self.data_dir / "tokens_vault.json"
        self._ensure_file()

    def _ensure_file(self):
        if not self.vault_file.exists():
            self._save([])

    def _save(self, tokens):
        self.vault_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.vault_file.with_name(f".{self.vault_file.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(tokens, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        try:
            replace_with_retry(tmp, self.vault_file)
        finally:
            tmp.unlink(missing_ok=True)

    def list_tokens(self, mask=True):
        if not self.vault_file.exists():
            return []
        try:
            with open(self.vault_file, "r", encoding="utf-8") as f:
                tokens = json.load(f)
            
            # Clean up / reset hourly usage if needed
            now_ts = time.time()
            changed = False
            for t in tokens:
                window_start = t.get("usage_window_start", 0)
                if now_ts - window_start > 3600:
                    t["usage_window_start"] = now_ts
                    t["call_count_hour"] = 0
                    if t.get("rate_status") == "COOLDOWN_80":
                        t["rate_status"] = "NORMAL"
                    changed = True
            if changed:
                self._save(tokens)

            res = []
            for item in tokens:
                t = dict(item)
                raw = t.get("token", "")
                if mask:
                    if len(raw) > 12:
                        t["token_masked"] = raw[:6] + "..." + raw[-4:]
                    else:
                        t["token_masked"] = "***"
                    t.pop("token", None)
                res.append(t)
            return res
        except Exception:
            return []

    def get_raw_token(self, token_id):
        try:
            with open(self.vault_file, "r", encoding="utf-8") as f:
                tokens = json.load(f)
            for t in tokens:
                if t.get("id") == token_id:
                    return t.get("token")
        except Exception:
            pass
        return None

    def get_token_by_id(self, token_id):
        try:
            with open(self.vault_file, "r", encoding="utf-8") as f:
                tokens = json.load(f)
            for t in tokens:
                if t.get("id") == token_id:
                    return t
        except Exception:
            pass
        return None

    def add_token(self, name, token_str, kind="SYS", note="", discover_pages=True):
        """Store one token; optionally avoid the expensive /me/accounts discovery call."""
        token_str = token_str.strip()
        tokens = []
        if self.vault_file.exists():
            try:
                with open(self.vault_file, "r", encoding="utf-8") as f:
                    tokens = json.load(f)
            except Exception:
                tokens = []

        status_info = self.verify_token(token_str) if discover_pages else self.verify_identity(token_str)
        token_id = f"tok_{int(datetime.now().timestamp())}_{len(tokens)+1}"
        owner_name = status_info.get("owner_name", "").strip()
        resolved_name = name.strip() if name and name.strip() else (owner_name or f"Token {len(tokens)+1}")

        entry = {
            "id": token_id,
            "name": resolved_name,
            "owner_name": owner_name,
            "kind": kind,
            "token": token_str,
            "status": status_info.get("status", "ACTIVE"),
            "error_msg": status_info.get("error", ""),
            "pages_count": len(status_info.get("pages", [])),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "note": note,
            # Rate limit & Health fields
            "app_usage_pct": 0,
            "cputime_pct": 0,
            "time_pct": 0,
            "rate_status": "NORMAL", # NORMAL, WARNING_60, COOLDOWN_80, RATE_LIMITED
            "call_count_hour": 0,
            "usage_window_start": time.time(),
            "total_calls": 0,
            "last_used": None
        }

        tokens = [t for t in tokens if t.get("token") != token_str]
        tokens.append(entry)
        self._save(tokens)
        return entry, status_info.get("pages", [])

    def delete_token(self, token_id):
        if not self.vault_file.exists():
            return False
        try:
            with open(self.vault_file, "r", encoding="utf-8") as f:
                tokens = json.load(f)
            before = len(tokens)
            tokens = [t for t in tokens if t.get("id") != token_id]
            if len(tokens) == before:
                return False
            self._save(tokens)
            return True
        except Exception:
            return False

    def delete_tokens(self, token_ids):
        """Remove a validated set in one vault write; return the IDs removed."""
        with open(self.vault_file, "r", encoding="utf-8") as f:
            tokens = json.load(f)
        ids = set(token_ids)
        found = {str(item.get("id")) for item in tokens} & ids
        if found != ids:
            raise ValueError("Token không tồn tại: " + ", ".join(sorted(ids - found)))
        self._save([item for item in tokens if str(item.get("id")) not in ids])
        return sorted(found)

    def verify_identity(self, token_str):
        """Validate a token without enumerating its managed Pages."""
        token_str = token_str.strip()
        try:
            response = requests.get(
                "https://graph.facebook.com/v22.0/me",
                params={"access_token": token_str, "fields": "id,name"},
                timeout=10
            )
            data = response.json()
            if "error" in data:
                err = data["error"]
                return {
                    "status": "ERROR",
                    "error": f"[{err.get('code')}] {err.get('message')}",
                    "pages": [],
                    "owner_name": "",
                }
            return {
                "status": "ACTIVE",
                "error": "",
                "pages": [],
                "owner_name": str(data.get("name") or "").strip(),
            }
        except Exception as exc:
            return {"status": "ERROR", "error": str(exc), "pages": [], "owner_name": ""}

    def verify_token(self, token_str):
        token_str = token_str.strip()
        identity = self.verify_identity(token_str)
        owner_name = identity.get("owner_name", "")
        if identity.get("status") != "ACTIVE":
            return identity

        return self.discover_pages(token_str, owner_name=owner_name)

    def discover_pages(self, token_str, owner_name=""):
        """Enumerate managed Pages after identity validation has already succeeded."""
        token_str = token_str.strip()

        url = "https://graph.facebook.com/v22.0/me/accounts"
        params = {
            "access_token": token_str,
            "fields": "id,name,category,access_token,tasks,picture{url}",
            "limit": 100
        }
        try:
            resp = requests.get(url, params=params, timeout=12)
            data = resp.json()
            if "error" in data:
                err = data["error"]
                return {
                    "status": "ERROR",
                    "error": f"[{err.get('code')}] {err.get('message')}",
                    "pages": [],
                    "owner_name": owner_name,
                }
            
            pages = []
            seen = set()
            for page_number in range(50):
                for item in data.get("data", []):
                    page_id = str(item.get("id") or "")
                    if not page_id or page_id in seen:
                        continue
                    seen.add(page_id)
                    pages.append({
                        "page_id": page_id,
                        "page_name": item.get("name"),
                        "category": item.get("category", ""),
                        "page_token": item.get("access_token"),
                        "tasks": item.get("tasks") or [],
                        "avatar": item.get("picture", {}).get("data", {}).get("url", "")
                    })
                next_url = (data.get("paging") or {}).get("next")
                if not next_url:
                    break
                if not str(next_url).startswith("https://graph.facebook.com/"):
                    raise ValueError("Unexpected Page discovery pagination URL")
                data = requests.get(next_url, timeout=12).json()
                if "error" in data:
                    raise ValueError("Page discovery pagination failed")
            else:
                raise ValueError("Page discovery exceeded 50 pages of results")
            return {
                "status": "ACTIVE",
                "error": "",
                "pages": pages,
                "owner_name": owner_name
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e),
                "pages": [],
                "owner_name": owner_name,
            }

    def record_page_sync(self, token_id, pages):
        """Persist Page discovery metadata without changing identity-valid token status."""
        tokens = self.list_tokens(mask=False)
        entry = next((item for item in tokens if item.get("id") == token_id), None)
        if entry is None:
            return None
        entry["pages_count"] = len(pages or [])
        entry["last_checked"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._save(tokens)
        return entry

    def refresh_token_pages(self, token_id):
        """Explicitly re-run full Page discovery for one stored token."""
        tokens = self.list_tokens(mask=False)
        entry = next((item for item in tokens if item.get("id") == token_id), None)
        if not entry:
            return None, []
        status_info = self.verify_token(entry.get("token", ""))
        entry["status"] = status_info.get("status", "ERROR")
        entry["error_msg"] = status_info.get("error", "")
        entry["owner_name"] = status_info.get("owner_name", entry.get("owner_name", ""))
        entry["pages_count"] = len(status_info.get("pages", []))
        entry["last_checked"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._save(tokens)
        return entry, status_info.get("pages", [])

    def record_usage(self, token_id_or_token, response_headers=None):
        """Ghi nhận lượt gọi API và phân tích Header Rate Limit (X-App-Usage) của Meta"""
        if not self.vault_file.exists():
            return
        try:
            with open(self.vault_file, "r", encoding="utf-8") as f:
                tokens = json.load(f)
            
            now_ts = time.time()
            for t in tokens:
                is_match = False
                if t.get("id") == token_id_or_token or t.get("token") == token_id_or_token:
                    is_match = True
                
                if is_match:
                    t["total_calls"] = t.get("total_calls", 0) + 1
                    t["last_used"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    window_start = t.get("usage_window_start", now_ts)
                    if now_ts - window_start > 3600:
                        t["usage_window_start"] = now_ts
                        t["call_count_hour"] = 1
                    else:
                        t["call_count_hour"] = t.get("call_count_hour", 0) + 1

                    # Parse X-App-Usage header nếu có từ Meta Graph API
                    if response_headers:
                        app_usage_str = response_headers.get("x-app-usage") or response_headers.get("X-App-Usage")
                        if app_usage_str:
                            try:
                                usage = json.loads(app_usage_str)
                                call_pct = usage.get("call_count", 0)
                                cpu_pct = usage.get("total_cputime", 0)
                                time_pct = usage.get("total_time", 0)
                                t["app_usage_pct"] = call_pct
                                t["cputime_pct"] = cpu_pct
                                t["time_pct"] = time_pct
                                max_pct = max(call_pct, cpu_pct, time_pct)
                                
                                if max_pct >= 80:
                                    t["rate_status"] = "COOLDOWN_80"
                                elif max_pct >= 60:
                                    t["rate_status"] = "WARNING_60"
                                else:
                                    t["rate_status"] = "NORMAL"
                            except Exception:
                                pass

                    self._save(tokens)
                    break
        except Exception:
            pass

    def get_healthy_token_for_page(self, token_pool_ids=None):
        """Chọn token còn khỏe nhất (<80% usage) trong pool để đăng bài"""
        tokens = self.list_tokens(mask=False)
        active_tokens = [t for t in tokens if t.get("status") == "ACTIVE"]
        
        if token_pool_ids:
            active_tokens = [t for t in active_tokens if t.get("id") in token_pool_ids]

        if not active_tokens:
            return None

        # Lọc các token chưa chạm 80%
        healthy = [t for t in active_tokens if t.get("rate_status") != "COOLDOWN_80" and t.get("app_usage_pct", 0) < 80]
        if not healthy:
            # Fallback nếu tất cả đều quá 80%, chọn token có usage nhỏ nhất
            healthy = active_tokens
        
        # Sắp xếp theo: usage_pct tăng dần, call_count_hour tăng dần
        healthy.sort(key=lambda x: (x.get("app_usage_pct", 0), x.get("call_count_hour", 0)))
        return healthy[0]

    def auto_balance_group(self, page_count: int, available_token_ids=None):
        """Gợi ý tỷ lệ chia token: tối ưu chuẩn 30 pages / 10 tokens (~ 3 pages/token)"""
        tokens = self.list_tokens(mask=True)
        active_tokens = [t for t in tokens if t.get("status") == "ACTIVE"]
        if available_token_ids:
            active_tokens = [t for t in active_tokens if t.get("id") in available_token_ids]
        
        import math
        # Mỗi token tối ưu phụ trách 3 pages để giữ quota an toàn dưới 80%
        PAGES_PER_TOKEN = 3
        recommended_tokens_count = max(1, math.ceil(page_count / PAGES_PER_TOKEN))
        
        selected_tokens = active_tokens[:recommended_tokens_count]
        return {
            "page_count": page_count,
            "recommended_tokens_count": recommended_tokens_count,
            "ratio": f"~{PAGES_PER_TOKEN} pages / 1 token",
            "available_active_tokens": len(active_tokens),
            "suggested_token_ids": [t["id"] for t in selected_tokens],
            "tokens_summary": selected_tokens
        }
