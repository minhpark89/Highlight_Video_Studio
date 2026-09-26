import json
from pathlib import Path

posts_path = Path(r"D:\Highlight_Video_Studio\posts.json")
posts = json.loads(posts_path.read_text(encoding="utf-8")) if posts_path.exists() else []

print("Total posts:", len(posts))
for p in posts:
    print(f"ID: {p['id']}, Page: {p.get('page_name')}, Sched: {p.get('scheduled_time')}, Status: {p.get('status')}, Err: {p.get('error')}")
