import json
from pathlib import Path

# 1. Clear posted_clips.json
p = Path(r"D:\Highlight_Video_Studio\posted_clips.json")
p.write_text("[]", encoding="utf-8")
print("Reset posted_clips.json to []")

# 2. Clear posts.json
posts_file = Path(r"D:\Highlight_Video_Studio\posts.json")
posts_file.write_text("[]", encoding="utf-8")
print("Reset posts.json to []")
