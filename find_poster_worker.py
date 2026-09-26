from pathlib import Path
import re

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

matches = [line for line in app_text.splitlines() if 'publish' in line.lower() or 'schedule' in line.lower() or 'background' in line.lower() or 'worker' in line.lower()]
print("Matching lines count:", len(matches))
for m in matches[:40]:
    if 'def ' in m or 'class ' in m or 'Thread' in m:
        print(m)
