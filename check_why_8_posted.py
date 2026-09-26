import json
from pathlib import Path

# Check posted_clips.json
p = Path(r"D:\Highlight_Video_Studio\posted_clips.json")
posted = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
print(f"posted_clips.json: {len(posted)} items -> {posted}")

# Check posts.json
posts_file = Path(r"D:\Highlight_Video_Studio\posts.json")
posts = json.loads(posts_file.read_text(encoding="utf-8")) if posts_file.exists() else []
print(f"posts.json: {len(posts)} items")
for post in posts:
    print(f"  ID: {post['id']} | Page: {post.get('page_name')} | Status: {post.get('status')} | Clip: {post.get('media_file') or post.get('clip_filename')}")
