import json
import os
import hashlib
import uuid
from pathlib import Path
from datetime import datetime

class PageManager:
    def __init__(self, data_dir=r"D:\Highlight_Video_Studio"):
        self.data_dir = Path(data_dir)
        self.pages_file = self.data_dir / "pages.json"
        self.groups_file = self.data_dir / "page_groups.json"
        self._ensure_files()

    def _ensure_files(self):
        if not self.pages_file.exists():
            self._atomic_write(self.pages_file, [])
        if not self.groups_file.exists():
            self._atomic_write(self.groups_file, [])

    @staticmethod
    def _atomic_write(path, value):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(value, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)

    @staticmethod
    def credential_fingerprint(token_value):
        raw = str(token_value or "").encode("utf-8")
        return hashlib.sha256(raw).hexdigest() if raw else ""

    def list_pages(self):
        try:
            with open(self.pages_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
                # Older preview builds could leave scalar/invalid entries in
                # pages.json after an interrupted sync.  Never expose those
                # records to callers that expect Page dictionaries.
                return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []
        except Exception:
            return []

    def save_pages(self, pages):
        self._atomic_write(self.pages_file, pages)

    def sync_pages_from_token(self, token_entry, pages_data):
        current_pages = self.list_pages()
        token_id = token_entry.get("id")
        token_name = token_entry.get("name")
        if not token_id:
            raise ValueError("Cannot persist Page mapping without token_id")
        verified_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        credential_fingerprint = self.credential_fingerprint(token_entry.get("token"))
        discovered_ids = set()

        for p in pages_data if isinstance(pages_data, list) else []:
            if not isinstance(p, dict):
                continue
            page_id = str(p.get("page_id") or p.get("id") or "").strip()
            page_token = str(p.get("page_token") or p.get("access_token") or "").strip()
            if not page_id or not page_token:
                continue
            discovered_ids.add(page_id)
            existing = next((item for item in current_pages if str(item.get("page_id") or "") == page_id), None)
            binding = {
                "token_id": token_id,
                "token_name": token_name,
                "page_token": page_token,
                "verified_page_id": page_id,
                "verified_at": verified_at,
                "credential_fingerprint": credential_fingerprint,
                "tasks": [str(task).upper() for task in (p.get("tasks") or [])],
                "status": "VERIFIED",
            }
            if existing:
                existing["page_name"] = p.get("page_name")
                existing["category"] = p.get("category")
                existing["avatar"] = p.get("avatar")
                bindings = dict(existing.get("token_bindings") or {})
                bindings[token_id] = binding
                existing["token_bindings"] = bindings
                # Preserve an already verified canonical credential when a Page is
                # managed by multiple credentials; otherwise use this discovery.
                canonical_id = str(existing.get("token_id") or "")
                if canonical_id not in bindings:
                    canonical_id = token_id
                canonical = bindings[canonical_id]
                existing.update({
                    "page_token": canonical["page_token"],
                    "token_id": canonical_id,
                    "token_name": canonical.get("token_name"),
                    "mapping_verified_at": canonical.get("verified_at"),
                    "mapping_status": "VERIFIED",
                    "last_synced": verified_at,
                })
            else:
                current_pages.append({
                    "page_id": page_id,
                    "page_name": p.get("page_name"),
                    "category": p.get("category"),
                    "avatar": p.get("avatar"),
                    "page_token": page_token,
                    "token_id": token_id,
                    "token_name": token_name,
                    "token_bindings": {token_id: binding},
                    "mapping_verified_at": verified_at,
                    "mapping_status": "VERIFIED",
                    "group_ids": [],
                    "status": "ACTIVE",
                    "last_synced": verified_at,
                    "total_posted": 0
                })

        # A successful refresh is authoritative for this credential. Remove Page
        # bindings it no longer returns, without disturbing bindings from others.
        for page in current_pages:
            page_id = str(page.get("page_id") or "")
            bindings = dict(page.get("token_bindings") or {})
            if token_id in bindings and page_id not in discovered_ids:
                bindings.pop(token_id, None)
                page["token_bindings"] = bindings
                if str(page.get("token_id") or "") == token_id:
                    replacement_id = next(iter(bindings), "")
                    if replacement_id:
                        replacement = bindings[replacement_id]
                        page.update({
                            "page_token": replacement.get("page_token", ""),
                            "token_id": replacement_id,
                            "token_name": replacement.get("token_name", ""),
                            "mapping_status": "VERIFIED",
                            "mapping_verified_at": replacement.get("verified_at", ""),
                        })
                    else:
                        page.pop("page_token", None)
                        page["token_id"] = ""
                        page["token_name"] = ""
                        page["mapping_status"] = "MISSING"
                        page["mapping_verified_at"] = ""
        self.save_pages(current_pages)
        return current_pages

    def resolve_verified_mapping(self, page_id, token_entry=None):
        """Resolve only an exact discovery-backed Page/credential binding."""
        page_id = str(page_id or "").strip()
        page = next((p for p in self.list_pages() if str(p.get("page_id") or "") == page_id), None)
        if not page:
            return None, "missing_page"
        canonical_id = str(page.get("token_id") or "").strip()
        token_id = str((token_entry or {}).get("id") or canonical_id).strip()
        if not token_id:
            return None, "missing_mapping"
        binding = (page.get("token_bindings") or {}).get(token_id)
        if not binding or str(binding.get("verified_page_id") or "") != page_id:
            return None, "missing_mapping"
        if binding.get("status") != "VERIFIED" or not binding.get("page_token"):
            return None, "stale_mapping"
        if token_entry is None or str(token_entry.get("id") or "") != token_id:
            return None, "missing_credential"
        if token_entry.get("status") != "ACTIVE":
            return None, "stale_credential"
        fingerprint = self.credential_fingerprint(token_entry.get("token"))
        if not fingerprint or fingerprint != binding.get("credential_fingerprint"):
            return None, "stale_mapping"
        return {
            "page_id": page_id,
            "page_name": page.get("page_name", page_id),
            "token_id": token_id,
            "token_name": binding.get("token_name") or token_entry.get("name"),
            "page_token": binding.get("page_token"),
            "verified_at": binding.get("verified_at"),
            "credential_fingerprint": binding.get("credential_fingerprint"),
            "tasks": list(binding.get("tasks") or []),
        }, None

    def mapping_health(self):
        pages = self.list_pages()
        tokens = {}
        for page in pages:
            token_id = str(page.get("token_id") or "")
            if token_id:
                tokens[token_id] = tokens.get(token_id, 0) + 1
        verified = sum(1 for p in pages if p.get("mapping_status") == "VERIFIED" and p.get("token_id"))
        return {
            "total_pages": len(pages),
            "verified": verified,
            "unhealthy": len(pages) - verified,
            "mapped_credentials": len(tokens),
        }

    def list_groups(self):
        try:
            with open(self.groups_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
                return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []
        except Exception:
            return []

    def save_groups(self, groups):
        self._atomic_write(self.groups_file, groups)

    def add_or_update_group(self, group_id, name, page_ids, folder_binding=r"D:\Highlight_Video_Studio\output", schedule_config=None):
        groups = self.list_groups()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not group_id:
            group_id = f"grp_{int(datetime.now().timestamp())}_{len(groups)+1}"
            entry = {
                "id": group_id,
                "name": name,
                "page_ids": page_ids or [],
                "folder_binding": folder_binding,
                "schedule_config": schedule_config or {"stagger_minutes": 15, "times": ["11:30", "19:30"]},
                "created_at": now_str,
                "updated_at": now_str
            }
            groups.append(entry)
        else:
            for g in groups:
                if g.get("id") == group_id:
                    g["name"] = name
                    g["page_ids"] = page_ids or []
                    g["folder_binding"] = folder_binding
                    if schedule_config:
                        g["schedule_config"] = schedule_config
                    g["updated_at"] = now_str
                    entry = g
                    break
            else:
                entry = {
                    "id": group_id,
                    "name": name,
                    "page_ids": page_ids or [],
                    "folder_binding": folder_binding,
                    "schedule_config": schedule_config or {"stagger_minutes": 15, "times": ["11:30", "19:30"]},
                    "created_at": now_str,
                    "updated_at": now_str
                }
                groups.append(entry)
        
        self.save_groups(groups)
        return entry

    def delete_group(self, group_id):
        groups = self.list_groups()
        groups = [g for g in groups if g.get("id") != group_id]
        self.save_groups(groups)
        return True
