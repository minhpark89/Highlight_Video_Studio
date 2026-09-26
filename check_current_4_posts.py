import json
from pathlib import Path

posts_path = Path(r"D:\Highlight_Video_Studio\posts.json")
posts = json.loads(posts_path.read_text(encoding="utf-8"))
print("Total posts:", len(posts))
for p in posts:
    print(f"ID: {p.get('id')}, Status: {p.get('status')}, Scheduled: {p.get('scheduled_time')}, Page: {p.get('page_name')}")
    print(f"  Comment: {p.get('comment')}")
