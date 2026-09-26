import json
from pathlib import Path

# 1. Check page_groups.json
groups_file = Path(r"D:\Highlight_Video_Studio\page_groups.json")
if groups_file.exists():
    groups = json.loads(groups_file.read_text(encoding="utf-8"))
    print("=== Groups in page_groups.json ===")
    for g in groups:
        print(f"ID: {g.get('id')}, Name: {g.get('name')}, Times: {g.get('schedule_config', {}).get('times')}, Pages: {len(g.get('page_ids', []))}")
else:
    print("page_groups.json does not exist")

# 2. Check posted_clips.json
posted_file = Path(r"D:\Highlight_Video_Studio\posted_clips.json")
if posted_file.exists():
    posted = json.loads(posted_file.read_text(encoding="utf-8"))
    print(f"\nposted_clips.json count: {len(posted)}")
else:
    print("posted_clips.json does not exist")

# 3. Check posts.json
posts_file = Path(r"D:\Highlight_Video_Studio\posts.json")
if posts_file.exists():
    posts = json.loads(posts_file.read_text(encoding="utf-8"))
    print(f"\nposts.json count: {len(posts)}")
    for p in posts:
        print(f"ID: {p.get('id')}, Status: {p.get('status')}, Scheduled: {p.get('scheduled_time')}, Err: {p.get('error')}")
