from pathlib import Path
import re

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where 'pages-cards-container' is populated
pos = html.find("pages-cards-container")
matches = []
while pos != -1:
    matches.append(pos)
    pos = html.find("pages-cards-container", pos+1)

print("Found occurrences of pages-cards-container:", matches)
for p in matches:
    print(f"--- Pos {p} ---")
    print(html[max(0, p-60):min(len(html), p+350)])
