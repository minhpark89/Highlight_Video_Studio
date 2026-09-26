import json
from pathlib import Path

# Create a sample post if posts.json is empty or doesn't exist
POSTS_FILE = Path(r"D:\Highlight_Video_Studio\posts.json")
if not POSTS_FILE.exists():
    POSTS_FILE.write_text("[]", encoding="utf-8")

# Let's verify posts.json
print("posts.json exists:", POSTS_FILE.exists())
