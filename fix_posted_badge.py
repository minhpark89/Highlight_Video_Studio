import json
from pathlib import Path

# 1. Reset posted_clips.json
posted_file = Path(r"D:\Highlight_Video_Studio\posted_clips.json")
posted_file.write_text("[]", encoding="utf-8")
print("Reset posted_clips.json to []")

# 2. Check posts.json
posts_file = Path(r"D:\Highlight_Video_Studio\posts.json")
if posts_file.exists():
    posts = json.loads(posts_file.read_text(encoding="utf-8"))
    for p in posts:
        print(f"Post {p['id']}: Status={p.get('status')}, Error={p.get('error')}")
