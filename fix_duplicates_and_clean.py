import json
from pathlib import Path

# Fix 1: Reset posted_clips.json
posted_file = Path(r"D:\Highlight_Video_Studio\posted_clips.json")
posted_file.write_text("[]", encoding="utf-8")
print("Reset posted_clips.json to []")

# Fix 2: Reset posts.json
posts_file = Path(r"D:\Highlight_Video_Studio\posts.json")
posts_file.write_text("[]", encoding="utf-8")
print("Reset posts.json to []")

# Fix 3: Remove duplicate nhóm 1 in page_groups.json
groups_file = Path(r"D:\Highlight_Video_Studio\page_groups.json")
if groups_file.exists():
    groups = json.loads(groups_file.read_text(encoding="utf-8"))
    print("Old groups count:", len(groups))
    # Deduplicate by name, keep the latest updated one
    seen_names = {}
    for g in groups:
        seen_names[g["name"]] = g
    clean_groups = list(seen_names.values())
    groups_file.write_text(json.dumps(clean_groups, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Cleaned groups count:", len(clean_groups))
    for g in clean_groups:
        print(f"  {g['id']}: {g['name']} - times: {g.get('schedule_config', {}).get('times')}")
