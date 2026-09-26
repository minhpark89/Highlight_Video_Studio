import json
from datetime import datetime
from pathlib import Path

posts_path = Path(r"D:\Highlight_Video_Studio\posts.json")
posts = json.loads(posts_path.read_text(encoding="utf-8"))
now = datetime.now()
print("Now:", now.strftime("%Y-%m-%d %H:%M:%S"))

for p in posts:
    sched_dt = datetime.strptime(p["scheduled_time"], "%Y-%m-%d %H:%M:%S")
    is_due = sched_dt <= now
    print(f"Post {p['id']}: Sched={p['scheduled_time']} | Due={is_due} | Status={p['status']} | Page={p['page_name']}")
