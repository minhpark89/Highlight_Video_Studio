with open("D:/Highlight_Video_Studio/web/app.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = re.findall(r'@app\.route\([\'\"](.*?)[\'\"].*?\)\ndef (\w+)', text)
for r, fn in matches:
    if "web" in r or "setting" in r or "config" in r:
        print(f"Route: {r} -> {fn}")
