import json
from pathlib import Path

posts_path = Path(r"D:\Highlight_Video_Studio\posts.json")
posts = json.loads(posts_path.read_text(encoding="utf-8")) if posts_path.exists() else []

for p in posts:
    print(f"ID: {p['id']}, Page: {p['page_name']}, Status: {p['status']}, Sched: {p['scheduled_time']}, PostFBId: {p.get('post_fb_id')}")
