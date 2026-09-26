from pathlib import Path
import json

# 1. Inspect posted_clips.json
posted_file = Path(r"D:\Highlight_Video_Studio\posted_clips.json")
posted = json.loads(posted_file.read_text(encoding="utf-8")) if posted_file.exists() else []
print(f"posted_clips.json count: {len(posted)}")

# 2. Inspect posts.json
posts_file = Path(r"D:\Highlight_Video_Studio\posts.json")
posts = json.loads(posts_file.read_text(encoding="utf-8")) if posts_file.exists() else []
print(f"posts.json count: {len(posts)}")
for p in posts:
    print(f"Post {p['id']}: Status={p.get('status')}, Sched={p.get('scheduled_time')}, Err={p.get('error')}")
