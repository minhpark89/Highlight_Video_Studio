import json
from pathlib import Path
import requests

# 1. Clear posted_clips.json
p = Path(r"D:\Highlight_Video_Studio\posted_clips.json")
p.write_text("[]", encoding="utf-8")
print("Reset posted_clips.json to []")

# 2. Clear posts.json
posts_file = Path(r"D:\Highlight_Video_Studio\posts.json")
posts_file.write_text("[]", encoding="utf-8")
print("Reset posts.json to []")

# 3. Test API /api/clips to make sure it returns 0 posted
rc = requests.get("http://127.0.0.1:5080/api/clips")
clips = rc.json()
posted_cnt = len([c for c in clips if c.get("is_posted")])
print(f"Total clips: {len(clips)}, is_posted: {posted_cnt}")
