import json
from pathlib import Path

# Reset posts.json completely clean
posts_path = Path(r"D:\Highlight_Video_Studio\posts.json")
posts_path.write_text("[]", encoding="utf-8")
print("Reset posts.json to []")

# Reset posted_clips.json completely clean
posted_path = Path(r"D:\Highlight_Video_Studio\posted_clips.json")
posted_path.write_text("[]", encoding="utf-8")
print("Reset posted_clips.json to []")
