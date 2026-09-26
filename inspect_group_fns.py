import os, json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# Check submitAddGroup and deleteGroup
for fn in ["submitAddGroup", "deleteGroup", "openAddGroupModal", "closeAddGroupModal"]:
    pos = text.find(f"function {fn}")
    print(f"function {fn}:", pos)
    if pos != -1:
        print(text[pos:pos+400])
