import json
from pathlib import Path
from datetime import datetime

posts_path = Path(r"D:\Highlight_Video_Studio\posts.json")
posts = json.loads(posts_path.read_text(encoding="utf-8"))
print("Current time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
for p in posts:
    print(f"Post {p['id']}: Status={p['status']}, Sched={p['scheduled_time']}, Page={p['page_name']}")
