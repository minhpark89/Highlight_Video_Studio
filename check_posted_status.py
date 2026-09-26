from pathlib import Path
import json

posted_file = Path(r"D:\Highlight_Video_Studio\posted_clips.json")
if posted_file.exists():
    posted = json.loads(posted_file.read_text(encoding="utf-8"))
    print("Total items in posted_clips.json:", len(posted))
    print("Sample items:", posted[:10])
else:
    print("posted_clips.json does not exist!")

# Also check posts.json
posts_file = Path(r"D:\Highlight_Video_Studio\posts.json")
if posts_file.exists():
    posts = json.loads(posts_file.read_text(encoding="utf-8"))
    print("Total posts in posts.json:", len(posts))
    for p in posts:
        print(f"Post {p['id']} - status: {p.get('status')} - clip: {p.get('clip_filename') or p.get('media_file')} - err: {p.get('error')}")
