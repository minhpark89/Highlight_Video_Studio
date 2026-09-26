from pathlib import Path
import re

with open(r"D:\Highlight_Video_Studio\web\app.py", "r", encoding="utf-8") as f:
    text = f.read()

# Let's search for meta reel poster or publish functions
matches = re.findall(r'def\s+.*publish.*\(', text, re.IGNORECASE)
print("Publish functions in app.py:", matches)

# Check MetaReelPoster usage
pos_mp = text.find('MetaReelPoster')
print("MetaReelPoster found at:", pos_mp)
if pos_mp != -1:
    print(text[pos_mp-100:pos_mp+1500])
