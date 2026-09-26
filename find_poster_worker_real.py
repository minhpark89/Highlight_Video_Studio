from pathlib import Path
import re

text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

matches = [line for line in text.splitlines() if 'publish' in line.lower() or 'schedule' in line.lower() or 'worker' in line.lower() or 'thread' in line.lower()]
print("Matching lines count:", len(matches))
for m in matches[:50]:
    if 'def ' in m or 'Thread' in m or 'while' in m or 'target=' in m:
        print(m)
