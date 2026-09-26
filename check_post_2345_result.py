import json
from pathlib import Path

posts = json.loads(Path(r"D:\Highlight_Video_Studio\posts.json").read_text(encoding="utf-8"))
for p in posts:
    print(f"ID: {p['id']}, Page: {p['page_name']}, Status: {p['status']}, post_fb_id: {p.get('post_fb_id')}")
