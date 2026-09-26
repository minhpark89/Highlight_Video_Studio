import json
from pathlib import Path

# 1. Inspect posted_clips.json
posted_file = Path(r"D:\Highlight_Video_Studio\posted_clips.json")
if posted_file.exists():
    posted = json.loads(posted_file.read_text(encoding="utf-8"))
    print("posted_clips.json:", len(posted), posted[:10])
else:
    print("posted_clips.json does not exist")

# 2. Check posts.json
posts_file = Path(r"D:\Highlight_Video_Studio\posts.json")
if posts_file.exists():
    posts = json.loads(posts_file.read_text(encoding="utf-8"))
    print("posts.json:", len(posts))
    for p in posts:
        print(f"ID: {p['id']}, Page: {p.get('page_name')}, Status: {p.get('status')}, PostFBId: {p.get('post_fb_id')}, Clip: {p.get('media_file') or p.get('clip_filename')}")
