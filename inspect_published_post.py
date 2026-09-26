import json
from pathlib import Path

posts_path = Path(r"D:\Highlight_Video_Studio\posts.json")
posts = json.loads(posts_path.read_text(encoding="utf-8")) if posts_path.exists() else []

print(f"Total posts: {len(posts)}")
for p in posts:
    print(f"Post {p['id']}: Status={p.get('status')}, Sched={p.get('scheduled_time')}, FB_ID={p.get('post_fb_id')}, Page={p.get('page_name')}")
