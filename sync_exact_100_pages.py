import json, shutil
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
NVS_DIR = Path(r"D:\News_Video_Studio")

print("[1/3] Syncing exact 100 pages from token_pages.json...")
nvs_file = NVS_DIR / "data" / "registry" / "token_pages.json"
hvs_pages_file = BASE_DIR / "pages.json"
hvs_groups_file = BASE_DIR / "page_groups.json"

shutil.copy2(hvs_pages_file, hvs_pages_file.with_suffix(".json.bak_130_backup"))

with open(nvs_file, "r", encoding="utf-8") as f:
    nvs_pages = json.load(f)

with open(hvs_pages_file, "r", encoding="utf-8") as f:
    hvs_all = json.load(f)

hvs_map = {str(p.get("page_id") or p.get("id")): p for p in hvs_all}

# Tạo nhóm mặc định "BM 1 (100 Page)" nếu chưa có
groups_data = [
    {
        "id": "group_bm1",
        "name": "BM 1 (Dàn 100 Page)",
        "folder_path": r"D:\Highlight_Video_Studio\output",
        "page_ids": [str(p.get("id") or p.get("page_id")) for p in nvs_pages],
        "created_at": "2026-09-24 10:00:00"
    }
]

with open(hvs_groups_file, "w", encoding="utf-8") as gf:
    json.dump(groups_data, gf, ensure_ascii=False, indent=2)
print("Updated page_groups.json with BM 1 group!")

# Xây dựng danh sách chuẩn 100 pages
exact_100 = []
for p in nvs_pages:
    pid = str(p.get("id") or p.get("page_id"))
    h = hvs_map.get(pid, {})
    
    avatar_url = h.get("avatar") or ""
    # Nếu không có avatar thật từ Facebook CDN, dùng avatar đại diện chất lượng cao
    if not avatar_url:
        avatar_url = f"https://graph.facebook.com/{pid}/picture?type=large"

    entry = {
        "page_id": pid,
        "page_name": p.get("name") or h.get("page_name") or f"Fanpage {pid}",
        "category": h.get("category") or "Community",
        "avatar": avatar_url,
        "page_token": h.get("page_token") or p.get("access_token_dpapi") or "",
        "token_name": p.get("system_user_name") or "System User",
        "group_ids": ["group_bm1"],
        "group_name": "BM 1 (Dàn 100 Page)",
        "status": "ACTIVE",
        "total_posted": h.get("total_posted", 0)
    }
    exact_100.append(entry)

with open(hvs_pages_file, "w", encoding="utf-8") as pf:
    json.dump(exact_100, pf, ensure_ascii=False, indent=2)

print(f"Sync complete! Exactly {len(exact_100)} pages saved to pages.json (all with avatar URL).")
