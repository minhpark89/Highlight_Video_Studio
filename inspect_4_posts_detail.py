import json
from pathlib import Path

posts_path = Path(r"D:\Highlight_Video_Studio\posts.json")
posts = json.loads(posts_path.read_text(encoding="utf-8"))
print("Current posts in posts.json:", len(posts))
for p in posts:
    print("---")
    print(f"ID: {p.get('id')}")
    print(f"Title: {p.get('title')}")
    print(f"Page: {p.get('page_name')} ({p.get('page_id')})")
    print(f"Scheduled Time: {p.get('scheduled_time')}")
    print(f"Status: {p.get('status')}")
    print(f"Comment: {p.get('comment')}")
    print(f"Token: {p.get('token', '')[:15]}...")
