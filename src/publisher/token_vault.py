import os
import json
import base64
import time
import requests
from pathlib import Path
from datetime import datetime

class TokenVault:
    def __init__(self, data_dir=r"D:\Highlight_Video_Studio"):
        self.data_dir = Path(data_dir)
        self.vault_file = self.data_dir / "tokens_vault.json"
        self._ensure_file()

    def _ensure_file(self):
        if not self.vault_file.exists():
            self._save([])

    def _save(self, tokens):
        with open(self.vault_file, "w", encoding="utf-8") as f:
            json.dump(tokens, f, indent=2, ensure_ascii=False)

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

    def add_token(self, name, token_str, kind="SYS", note=""):
        token_str = token_str.strip()
        tokens = []
        if self.vault_file.exists():
            try:
                with open(self.vault_file, "r", encoding="utf-8") as f:
                    tokens = json.load(f)
            except Exception:
                tokens = []

        status_info = self.verify_token(token_str)
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
            tokens = [t for t in tokens if t.get("id") != token_id]
            self._save(tokens)
            return True
        except Exception:
            return False

    def verify_token(self, token_str):
        token_str = token_str.strip()
        owner_name = ""
        try:
            me_resp = requests.get(
                "https://graph.facebook.com/v22.0/me",
                params={"access_token": token_str, "fields": "id,name"},
                timeout=10
            )
            me_data = me_resp.json()
            if "name" in me_data and me_data["name"]:
                owner_name = me_data["name"]
        except Exception:
            pass

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
                    "pages": []
                }
            
            pages = []
            for item in data.get("data", []):
                pages.append({
                    "page_id": item.get("id"),
                    "page_name": item.get("name"),
                    "category": item.get("category", ""),
                    "page_token": item.get("access_token"),
                    "avatar": item.get("picture", {}).get("data", {}).get("url", "")
                })
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
                "pages": []
            }

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
