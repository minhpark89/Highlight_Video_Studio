from pathlib import Path
import re

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where reel_poster is used in app.py
matches = [line for line in app_text.splitlines() if 'reel_poster' in line]
print("reel_poster matches:")
for m in matches:
    print(m)
