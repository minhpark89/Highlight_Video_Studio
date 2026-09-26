import json
from datetime import datetime
from pathlib import Path

posts_path = Path(r"D:\Highlight_Video_Studio\posts.json")
posts = json.loads(posts_path.read_text(encoding="utf-8"))
now = datetime.now()
print("Now:", now)
for p in posts:
    sched = datetime.strptime(p['scheduled_time'], "%Y-%m-%d %H:%M:%S")
    print(f"ID: {p['id']}, Page: {p['page_name']}, Sched: {sched}, Is Due: {sched <= now}, Status: {p['status']}")
