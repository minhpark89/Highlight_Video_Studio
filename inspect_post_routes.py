with open(r"D:\Highlight_Video_Studio\web\app.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = re.findall(r'@app\.route\([\'\"]([^\'\"]+)', text)
for m in matches:
    if any(k in m for k in ['publish', 'post', 'schedule', 'cron', 'run']):
        print("Route:", m)
