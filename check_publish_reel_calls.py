from pathlib import Path
import re

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

matches = [line for line in app_text.splitlines() if 'publish_reel' in line]
for m in matches:
    print(m)
