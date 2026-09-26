import json
from pathlib import Path

posts_path = Path(r"D:\Highlight_Video_Studio\posts.json")
posts = json.loads(posts_path.read_text(encoding="utf-8"))
for p in posts:
    print(f"ID: {p['id']}, Page: {p['page_name']}, Scheduled: {p['scheduled_time']}, Status: {p['status']}")
    print(f"First Comment: {p.get('first_comment') or p.get('comment')}")
