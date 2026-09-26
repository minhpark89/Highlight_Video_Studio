import json
from datetime import datetime
from pathlib import Path

posts_path = Path(r"D:\Highlight_Video_Studio\posts.json")
posts = json.loads(posts_path.read_text(encoding="utf-8"))

print(f"Posts count: {len(posts)}")
for p in posts:
    print(f"ID: {p['id']} | Page: {p['page_name']} | Time: {p['scheduled_time']} | Status: {p['status']}")
    print(f"  Comment: {p.get('first_comment')}")
