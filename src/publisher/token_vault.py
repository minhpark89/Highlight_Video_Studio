import os
import json
import base64
import time
import requests
import uuid
import threading
import re
from functools import wraps
from pathlib import Path
from datetime import datetime
from multi_pc.json_io import replace_with_retry
from src.publisher.meta_api import GRAPH_BASE_URL, bearer_headers, graph_error_message

_VAULT_LOCK = threading.RLock()
_PAGE_ACCESS_GUARD = threading.Lock()
_PAGE_ACCESS_LOCKS = {}
_PAGE_ACCESS_CACHE = {}

def vault_transaction(function):
    @wraps(function)
    def locked(*args, **kwargs):
        with _VAULT_LOCK:
            return function(*args, **kwargs)
    return locked

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

    @vault_transaction
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
            matches = [t for t in tokens if t.get("id") == token_id]
            if len(matches) == 1:
                return matches[0].get("token")
        except Exception:
            pass
        return None

    def get_token_by_id(self, token_id):
        try:
            with open(self.vault_file, "r", encoding="utf-8") as f:
                tokens = json.load(f)
            matches = [t for t in tokens if t.get("id") == token_id]
            if len(matches) == 1:
                return matches[0]
        except Exception:
            pass
        return None

    @vault_transaction
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
        existing = next((item for item in tokens if item.get("token") == token_str), None)
        token_id = str((existing or {}).get("id") or f"tok_{uuid.uuid4().hex}")
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
        for field in ("owner_id", "identity_valid", "verification_level", "permissions_status", "granted_permissions"):
            if field in status_info:
                entry[field] = status_info[field]
        entry["kind_verified"] = False  # SYS/USER is an operator label, not /debug_token evidence.

        if existing:
            # Re-importing the same credential refreshes its verification data,
            # while preserving IDs already referenced by Pages and queued posts.
            for field in ("created_at", "total_calls", "call_count_hour", "usage_window_start",
                          "last_used", "app_usage_pct", "cputime_pct", "time_pct", "rate_status"):
                if field in existing:
                    entry[field] = existing[field]
        tokens = [t for t in tokens if t.get("token") != token_str]
        tokens.append(entry)
        self._save(tokens)
        return entry, status_info.get("pages", [])

    @vault_transaction
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

    @vault_transaction
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
        """Verify identity only; /me success does not prove publish permissions."""
        token_str = token_str.strip()
        try:
            response = requests.get(
                f"{GRAPH_BASE_URL}/me",
                headers=bearer_headers(token_str), params={"fields": "id,name"},
                timeout=10
            )
            data = response.json()
            if not response.ok or not isinstance(data, dict) or data.get("error"):
                return {
                    "status": "ERROR",
                    "error": graph_error_message(data, token_str, response.status_code),
                    "pages": [], "owner_name": "", "identity_valid": False,
                    "definitive_identity_rejection": bool(response.status_code < 500 and isinstance(data, dict) and data.get("error")),
                }
            if not re.fullmatch(r"[0-9]+", str(data.get("id") or "")):
                raise ValueError("Missing Meta identity ID")
            return {
                "status": "ACTIVE",
                "error": "",
                "pages": [],
                "owner_name": str(data.get("name") or "").strip(),
                "owner_id": str(data["id"]), "identity_valid": True,
                "verification_level": "identity_only",
            }
        except (requests.RequestException, ValueError, TypeError):
            return {"status": "ERROR", "error": "Không xác minh được danh tính Meta; hãy kiểm tra kết nối và thử lại.",
                    "pages": [], "owner_name": "", "identity_valid": False,
                    "definitive_identity_rejection": False}

    def verify_token(self, token_str):
        token_str = token_str.strip()
        identity = self.verify_identity(token_str)
        owner_name = identity.get("owner_name", "")
        if identity.get("status") != "ACTIVE":
            return identity

        result = self.discover_pages(token_str, owner_name=owner_name)
        result.update(identity_valid=True, owner_id=identity.get("owner_id", ""))
        if result.get("status") == "ACTIVE":
            result.update(self.read_permissions(token_str))
        return result

    @staticmethod
    def _read_edge(token_str, path, params, timeout=12):
        """Read cursors through the fixed v24 endpoint; never follow token URLs."""
        params = dict(params)
        rows, seen_cursors = [], set()
        for _ in range(50):
            response = requests.get(f"{GRAPH_BASE_URL}/{path}", headers=bearer_headers(token_str),
                                    params=params, timeout=timeout)
            data = response.json()
            if not response.ok or not isinstance(data, dict) or data.get("error"):
                raise ValueError(graph_error_message(data, token_str, response.status_code))
            if not isinstance(data.get("data"), list):
                raise ValueError("Meta did not return a complete list of results.")
            rows.extend(data["data"])
            paging = data.get("paging") or {}
            if not isinstance(paging, dict):
                raise ValueError("Invalid Meta pagination response.")
            if not paging.get("next"):
                return rows
            cursors = paging.get("cursors") or {}
            cursor = cursors.get("after") if isinstance(cursors, dict) else None
            if not isinstance(cursor, str) or not cursor or cursor in seen_cursors:
                raise ValueError("Meta pagination cursor is missing or repeated.")
            seen_cursors.add(cursor)
            params["after"] = cursor
        raise ValueError("Meta discovery exceeded 50 result pages.")

    def read_permissions(self, token_str):
        """Best-effort scope introspection; unavailable is never treated as granted."""
        try:
            rows = self._read_edge(token_str, "me/permissions", {"limit": 100}, timeout=10)
            if not rows or not all(isinstance(row, dict) and row.get("permission") and row.get("status") for row in rows):
                raise ValueError("Unverified permission response")
            return {"permissions_status": "verified",
                    "granted_permissions": sorted({str(row["permission"]) for row in rows if row["status"] == "granted"})}
        except (requests.RequestException, ValueError, TypeError, AttributeError):
            return {"permissions_status": "unverified", "granted_permissions": []}

    def discover_pages(self, token_str, owner_name=""):
        """Enumerate managed Pages after identity validation has already succeeded."""
        token_str = token_str.strip()

        params = {
            "fields": "id,name,category,access_token,tasks,picture{url}",
            "limit": 100
        }
        try:
            pages = []
            seen = set()
            for item in self._read_edge(token_str, "me/accounts", params):
                if not isinstance(item, dict):
                    raise ValueError("Invalid Meta Page record.")
                page_id = str(item.get("id") or "")
                if not re.fullmatch(r"[0-9]+", page_id):
                    raise ValueError("Invalid Meta Page ID.")
                if page_id in seen:
                    continue
                seen.add(page_id)
                pages.append({
                    "page_id": page_id, "page_name": item.get("name"),
                    "category": item.get("category", ""), "page_token": item.get("access_token"),
                    "tasks": item.get("tasks") or [],
                    "avatar": (item.get("picture") or {}).get("data", {}).get("url", "")
                })
            return {
                "status": "ACTIVE",
                "error": "",
                "pages": pages,
                "owner_name": owner_name, "verification_level": "page_mapping",
            }
        except (requests.RequestException, ValueError, TypeError, AttributeError) as e:
            return {
                "status": "ERROR",
                "error": str(e) if isinstance(e, ValueError) and not isinstance(e, requests.RequestException)
                         else "Không đọc được danh sách Page từ Meta; hãy thử Sync lại.",
                "pages": [],
                "owner_name": owner_name,
            }

    @vault_transaction
    def record_verification(self, token_id, token_str, result):
        """Merge verification into the current vault, preserving concurrent usage."""
        entries = self.list_tokens(mask=False)
        entry = next((item for item in entries if item.get("id") == token_id and item.get("token") == token_str), None)
        if not entry:
            return None
        checked_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if result.get("status") == "ACTIVE" or result.get("definitive_identity_rejection"):
            entry.update(status=result["status"], error_msg=result.get("error", ""), last_checked=checked_at)
        for field in ("owner_id", "identity_valid", "verification_level", "permissions_status", "granted_permissions"):
            if field in result:
                entry[field] = result[field]
        if "permissions_status" in result:
            entry["permissions_checked_at"] = checked_at
        entry["page_access_status"] = result.get("status", "ERROR")
        entry["page_access_error"] = result.get("error", "")
        if result.get("status") == "ACTIVE":
            entry.update(pages_count=len(result.get("pages") or []), last_page_sync=checked_at,
                         owner_name=result.get("owner_name") or entry.get("owner_name", ""))
        self._save(entries)
        return dict(entry)

    def ensure_page_access(self, token_id, page_manager, *, max_age=300):
        """Refresh the exact root-to-Page mapping once per credential per 5 minutes.

        Failed discovery pauses writes for 60 seconds. No fallback credential or
        stale Page token is used after a failed refresh. Cache is process-local.
        """
        key = (str(self.vault_file.resolve()).casefold(), str(token_id))
        with _PAGE_ACCESS_GUARD:
            lock = _PAGE_ACCESS_LOCKS.setdefault(key, threading.Lock())
        with lock:
            entry = self.get_token_by_id(token_id)
            if not entry or not entry.get("token"):
                return {"ok": False, "error": "Credential nguồn không còn trong kho Token."}
            fingerprint = page_manager.credential_fingerprint(entry["token"])
            cached = _PAGE_ACCESS_CACHE.get(key)
            if cached and cached["fingerprint"] == fingerprint:
                ttl = max_age if cached["ok"] else 60
                if time.monotonic() - cached["checked_at"] < ttl:
                    return {"ok": cached["ok"], "error": cached["error"]}
            result = self.verify_token(entry["token"])
            current = self.record_verification(token_id, entry["token"], result)
            ok = bool(current and result.get("status") == "ACTIVE")
            if ok:
                page_manager.sync_pages_from_token(current, result.get("pages") or [], preserve_canonical=True)
            cached = {"ok": ok, "error": result.get("error", "") or ("" if ok else "Credential thay đổi trong lúc Sync; hãy thử lại."),
                      "fingerprint": fingerprint, "checked_at": time.monotonic()}
            _PAGE_ACCESS_CACHE[key] = cached
            return {"ok": cached["ok"], "error": cached["error"]}

    def pause_page_access(self, token_id, error):
        """Briefly stop new writes after Meta explicitly reports API access blocked."""
        from src.publisher.page_manager import PageManager
        from src.publisher.meta_api import safe_meta_text
        entry = self.get_token_by_id(token_id)
        if not entry:
            return
        key = (str(self.vault_file.resolve()).casefold(), str(token_id))
        with _PAGE_ACCESS_GUARD:
            _PAGE_ACCESS_CACHE[key] = {"ok": False, "error": safe_meta_text(error, entry.get("token")),
                                       "fingerprint": PageManager.credential_fingerprint(entry.get("token")),
                                       "checked_at": time.monotonic()}

    @vault_transaction
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

    @vault_transaction
    def record_identity_checks(self, outcomes):
        """Merge batch /me health results without overwriting Page sync or usage."""
        entries = self.list_tokens(mask=False)
        checked_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        by_id = {item.get("id"): item for item in entries}
        for probed, result in outcomes:
            entry = by_id.get(probed.get("id"))
            if not entry or entry.get("token") != probed.get("token"):
                continue
            entry.update(status=result.get("status", "ERROR"), error_msg=result.get("error", ""), last_checked=checked_at)
            for field in ("owner_id", "identity_valid", "owner_name"):
                if field in result and (field != "owner_name" or result[field]):
                    entry[field] = result[field]
        self._save(entries)

    @vault_transaction
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
        for field in ("owner_id", "identity_valid", "verification_level", "permissions_status", "granted_permissions"):
            if field in status_info:
                entry[field] = status_info[field]
        entry["page_access_status"] = status_info.get("status", "ERROR")
        entry["page_access_error"] = status_info.get("error", "")
        self._save(tokens)
        key = (str(self.vault_file.resolve()).casefold(), str(token_id))
        with _PAGE_ACCESS_GUARD:
            _PAGE_ACCESS_CACHE.pop(key, None)
        return entry, status_info.get("pages", [])

    @vault_transaction
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
