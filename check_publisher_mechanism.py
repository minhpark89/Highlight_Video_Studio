from pathlib import Path
import re

with open(r"D:\Highlight_Video_Studio\web\app.py", "r", encoding="utf-8") as f:
    text = f.read()

# Let's inspect where posts are processed
for kw in ['POSTS_FILE', 'def api_publish', 'def api_posts', 'schedule_worker', 'publisher']:
    pos = text.find(kw)
    print(kw, "at", pos)
    if pos != -1:
        print(text[pos:pos+300])
        print("---")
