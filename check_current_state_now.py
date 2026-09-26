import json
from pathlib import Path

# 1. Inspect why page_groups.json has 2 "nhóm 1"
groups_file = Path(r"D:\Highlight_Video_Studio\page_groups.json")
groups = json.loads(groups_file.read_text(encoding="utf-8")) if groups_file.exists() else []
print(f"Total groups in page_groups.json: {len(groups)}")
for g in groups:
    print(f"  ID: {g.get('id')} | Name: {g.get('name')} | Times: {g.get('schedule_config', {}).get('times')}")

# 2. Inspect posted_clips.json
posted_file = Path(r"D:\Highlight_Video_Studio\posted_clips.json")
posted = json.loads(posted_file.read_text(encoding="utf-8")) if posted_file.exists() else []
print(f"\nposted_clips.json count: {len(posted)}")

# 3. Inspect posts.json
posts_file = Path(r"D:\Highlight_Video_Studio\posts.json")
posts = json.loads(posts_file.read_text(encoding="utf-8")) if posts_file.exists() else []
print(f"\nposts.json count: {len(posts)}")
for p in posts:
    print(f"  Post {p.get('id')}: Status={p.get('status')} | Err={p.get('error')}")
