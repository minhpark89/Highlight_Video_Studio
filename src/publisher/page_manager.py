import os
import json
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
            with open(self.pages_file, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2, ensure_ascii=False)
        if not self.groups_file.exists():
            with open(self.groups_file, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2, ensure_ascii=False)

    def list_pages(self):
        try:
            with open(self.pages_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def save_pages(self, pages):
        with open(self.pages_file, "w", encoding="utf-8") as f:
            json.dump(pages, f, indent=2, ensure_ascii=False)

    def sync_pages_from_token(self, token_entry, pages_data):
        current_pages = self.list_pages()
        token_id = token_entry.get("id")
        
        for p in pages_data:
            page_id = p.get("page_id")
            existing = next((item for item in current_pages if item.get("page_id") == page_id), None)
            if existing:
                existing["page_name"] = p.get("page_name")
                existing["category"] = p.get("category")
                existing["avatar"] = p.get("avatar")
                existing["page_token"] = p.get("page_token")
                existing["token_id"] = token_id
                existing["last_synced"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                current_pages.append({
                    "page_id": page_id,
                    "page_name": p.get("page_name"),
                    "category": p.get("category"),
                    "avatar": p.get("avatar"),
                    "page_token": p.get("page_token"),
                    "token_id": token_id,
                    "group_ids": [],
                    "status": "ACTIVE",
                    "last_synced": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "total_posted": 0
                })
        self.save_pages(current_pages)
        return current_pages

    def list_groups(self):
        try:
            with open(self.groups_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def save_groups(self, groups):
        with open(self.groups_file, "w", encoding="utf-8") as f:
            json.dump(groups, f, indent=2, ensure_ascii=False)

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
