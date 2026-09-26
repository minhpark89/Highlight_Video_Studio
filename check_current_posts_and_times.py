import json
from pathlib import Path

# Check posts.json
posts_file = Path(r"D:\Highlight_Video_Studio\posts.json")
posts = json.loads(posts_file.read_text(encoding="utf-8")) if posts_file.exists() else []
print(f"Total posts currently in posts.json: {len(posts)}")
for p in posts:
    print(f"ID: {p.get('id')}, Page: {p.get('page_name')}, Sched: {p.get('scheduled_time')}, Status: {p.get('status')}")

# Check groups
groups_file = Path(r"D:\Highlight_Video_Studio\page_groups.json")
groups = json.loads(groups_file.read_text(encoding="utf-8")) if groups_file.exists() else []
print(f"\nTotal groups: {len(groups)}")
for g in groups:
    print(f"ID: {g.get('id')}, Name: {g.get('name')}, Times: {g.get('schedule_config', {}).get('times')}")
