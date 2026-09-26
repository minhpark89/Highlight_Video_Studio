import json
from pathlib import Path

# 1. Reset posted_clips.json completely
posted_file = Path(r"D:\Highlight_Video_Studio\posted_clips.json")
posted_file.write_text("[]", encoding="utf-8")
print("Reset posted_clips.json to []")

# 2. Reset posts.json completely
posts_file = Path(r"D:\Highlight_Video_Studio\posts.json")
posts_file.write_text("[]", encoding="utf-8")
print("Reset posts.json to []")

# 3. Clean up duplicated "nhóm 1" in page_groups.json
groups_file = Path(r"D:\Highlight_Video_Studio\page_groups.json")
groups = json.loads(groups_file.read_text(encoding="utf-8"))
print("Current groups in page_groups.json:", len(groups))

clean_groups = []
seen_names = set()
for g in reversed(groups):
    name = g.get("name")
    if name not in seen_names:
        seen_names.add(name)
        clean_groups.append(g)

clean_groups.reverse()
groups_file.write_text(json.dumps(clean_groups, indent=2, ensure_ascii=False), encoding="utf-8")
print("Deduplicated page_groups.json. Remaining groups:")
for g in clean_groups:
    print(f"  {g['id']}: {g['name']} | Times: {g.get('schedule_config', {}).get('times')}")
