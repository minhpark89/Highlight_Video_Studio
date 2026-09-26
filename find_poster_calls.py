with open(r"D:\Highlight_Video_Studio\web\app.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = re.findall(r'def\s+.*publish|def\s+.*schedule|MetaReelPoster', text)
print("Functions in app.py:", matches)

# Find where MetaReelPoster is instantiated or used
pos = text.find('MetaReelPoster')
while pos != -1:
    print("Found MetaReelPoster at:", pos)
    print(text[pos-100:pos+500])
    print("="*40)
    pos = text.find('MetaReelPoster', pos+1)
