import json
from pathlib import Path

# 1. Reset posted_clips.json
posted_file = Path(r"D:\Highlight_Video_Studio\posted_clips.json")
posted_file.write_text("[]", encoding="utf-8")
print("Reset posted_clips.json to []")

# 2. Reset posts.json
posts_file = Path(r"D:\Highlight_Video_Studio\posts.json")
posts_file.write_text("[]", encoding="utf-8")
print("Reset posts.json to []")

# 3. Clean and fix page_groups.json:
# Deduplicate "nhóm 1", keep only 1 "nhóm 1" (with latest times) and 1 "BM 1 (Dàn 100 Page)"
groups_file = Path(r"D:\Highlight_Video_Studio\page_groups.json")
if groups_file.exists():
    groups = json.loads(groups_file.read_text(encoding="utf-8"))
    dedup = {}
    for g in groups:
        # If name exists, keep the one with updated times or the latest
        name = g.get("name", "").strip()
        if name not in dedup:
            dedup[name] = g
        else:
            # Overwrite if current g has custom times
            if g.get("schedule_config", {}).get("times"):
                dedup[name] = g
    clean_list = list(dedup.values())
    groups_file.write_text(json.dumps(clean_list, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Cleaned page_groups.json to {len(clean_list)} groups:")
    for g in clean_list:
        print(f"  {g['id']}: {g['name']} | Times: {g.get('schedule_config', {}).get('times')}")
