import json
from pathlib import Path

# Check posted_clips.json
p = Path(r"D:\Highlight_Video_Studio\posted_clips.json")
posted = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
print(f"posted_clips.json current length: {len(posted)}")

# Check page_groups.json
g_path = Path(r"D:\Highlight_Video_Studio\page_groups.json")
groups = json.loads(g_path.read_text(encoding="utf-8")) if g_path.exists() else []
print(f"page_groups.json current count: {len(groups)}")
for g in groups:
    print(f"  ID: {g.get('id')} | Name: {g.get('name')} | Times: {g.get('schedule_config', {}).get('times')}")
