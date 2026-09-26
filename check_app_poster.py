with open(r"D:\Highlight_Video_Studio\web\app.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = re.findall(r'def\s+.*publish|MetaReelPoster', text)
print("Matches in app.py:", matches)
