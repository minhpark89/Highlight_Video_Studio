import json
from datetime import datetime
from pathlib import Path

posts_path = Path(r"D:\Highlight_Video_Studio\posts.json")
posts = json.loads(posts_path.read_text(encoding="utf-8"))
print("Current time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
for p in posts:
    print(f"Post {p['id']}:")
    print(f"  Page: {p['page_name']} ({p['page_id']})")
    print(f"  Scheduled: {p['scheduled_time']}")
    print(f"  Status: {p['status']}")
    print(f"  Comment: {p.get('first_comment')}")
