import json
from pathlib import Path

posts_path = Path(r"D:\Highlight_Video_Studio\posts.json")
posts = json.loads(posts_path.read_text(encoding="utf-8")) if posts_path.exists() else []

for p in posts:
    print("Post ID:", p.get("id"))
    print("  Page:", p.get("page_name"))
    print("  Status:", p.get("status"))
    print("  post_fb_id:", p.get("post_fb_id"))
    print("  video_id:", p.get("video_id"))
    print("  fb_url:", p.get("fb_url"))
    print("  comment_id:", p.get("comment_id"))
