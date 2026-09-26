import os, json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# Let's inspect from index 220000 to the end of pane-pages
pos = text.find("Cơ chế phát video")
print("Position:", pos)
start = max(0, pos - 800)
end = min(len(text), pos + 1200)

with open(BASE_DIR / "leaked_area.html", "w", encoding="utf-8") as out:
    out.write(text[start:end])

print(text[start:end])
