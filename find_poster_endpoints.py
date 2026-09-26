with open(r"D:\Highlight_Video_Studio\web\app.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'def\s+.*publish|MetaReelPoster', text)]
for idx in matches:
    print(text[idx:idx+400])
    print("="*40)
