import json
from pathlib import Path

posts_path = Path(r"D:\Highlight_Video_Studio\posts.json")
if posts_path.exists():
    posts = json.loads(posts_path.read_text(encoding="utf-8"))
    print("Total posts in posts.json:", len(posts))
    statuses = {}
    for p in posts:
        st = p.get("status", "unknown")
        statuses[st] = statuses.get(st, 0) + 1
    print("Status counts:", statuses)
