import json
from pathlib import Path

posts_path = Path(r"D:\Highlight_Video_Studio\posts.json")
posts = json.loads(posts_path.read_text(encoding="utf-8")) if posts_path.exists() else []

print("Total posts:", len(posts))
for p in posts:
    print(f"Post {p['id']}: Page={p.get('page_name')}, Status={p.get('status')}, Error={p.get('error')}")
