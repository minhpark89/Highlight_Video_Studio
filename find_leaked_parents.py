import os
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("Hỗ trợ Hashtags")
print("Position of 'Hỗ trợ Hashtags':", pos)

# Find what parent element contains this text
# Look backwards for id=" or class="
p = pos
for _ in range(20):
    p = text.rfind("<", 0, p)
    tag = text[p:p+60].replace("\n", " ")
    print(f"Tag at {p}: {tag}")
    if "section" in tag or "modal" in tag or "pane" in tag:
        break
