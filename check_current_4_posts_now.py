import json
from pathlib import Path
from datetime import datetime

posts_path = Path(r"D:\Highlight_Video_Studio\posts.json")
posts = json.loads(posts_path.read_text(encoding="utf-8"))

for p in posts:
    print(f"ID: {p['id']}, Page: {p['page_name']}, Scheduled: {p['scheduled_time']}, Status: {p['status']}")
