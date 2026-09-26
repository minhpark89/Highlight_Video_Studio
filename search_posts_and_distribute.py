with open("D:/Highlight_Video_Studio/web/app.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = re.findall(r'@app\.route\([\'\"](.*?)[\'\"].*?\)\ndef (\w+)', text)
for r, fn in matches:
    if any(k in r for k in ["distribute", "post", "clip", "schedule", "delete"]):
        print(f"Route: {r} -> {fn}")
