import os, json, re
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# Let's inspect modal-add-group and group management
print("Searching for group functions in index.html:")
for line in text.splitlines():
    if any(k in line.lower() for k in ["openaddgroupmodal", "deletegroup", "creategroup", "modal-add-group", "group-pages-select-box"]):
        print("  ", line.strip()[:100])
