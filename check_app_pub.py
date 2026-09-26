from pathlib import Path

with open(r"D:\Highlight_Video_Studio\web\app.py", "r", encoding="utf-8") as f:
    code = f.read()

import re
matches = re.findall(r'def\s+.*publish|def\s+.*post|POSTS_FILE', code)
print("Publish/Post references in app.py:", matches)

# Check api_publish_reel
pos = code.find("def api_publish_reel")
print(code[pos:pos+1500])
