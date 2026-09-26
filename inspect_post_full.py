import json
from pathlib import Path

posts = json.loads(Path(r"D:\Highlight_Video_Studio\posts.json").read_text(encoding="utf-8"))
for p in posts:
    print(p)
