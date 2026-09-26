import json
from pathlib import Path

posts_file = Path(r"D:\Highlight_Video_Studio\posts.json")
pages_file = Path(r"D:\Highlight_Video_Studio\pages.json")

pages = json.loads(pages_file.read_text(encoding="utf-8"))
page_token_map = {p.get("page_id"): p.get("token_name") for p in pages}

if posts_file.exists():
    posts = json.loads(posts_file.read_text(encoding="utf-8"))
    for post in posts:
        pid = post.get("page_id")
        if pid in page_token_map:
            post["token_name"] = page_token_map[pid]
    posts_file.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Updated {len(posts)} posts with distributed tokens!")
