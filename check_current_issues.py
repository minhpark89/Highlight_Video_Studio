from pathlib import Path
import json

# 1. Check posted_clips.json
p_file = Path(r"D:\Highlight_Video_Studio\posted_clips.json")
posted = json.loads(p_file.read_text(encoding="utf-8")) if p_file.exists() else []
print(f"posted_clips.json count: {len(posted)}")
print("Items in posted_clips.json:", posted)

# 2. Check posts.json
posts_file = Path(r"D:\Highlight_Video_Studio\posts.json")
posts = json.loads(posts_file.read_text(encoding="utf-8")) if posts_file.exists() else []
print(f"\nposts.json count: {len(posts)}")
for p in posts:
    print(f"ID: {p['id']}, Page: {p.get('page_name')}, Sched: {p.get('scheduled_time')}, Status: {p.get('status')}, PostID: {p.get('post_fb_id')}")
