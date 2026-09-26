import os, json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# Let's inspect where openAssignSingleTokenModal is defined in JS
pos = text.find("function openAssignSingleTokenModal")
print("openAssignSingleTokenModal pos:", pos)
if pos != -1:
    print(text[pos:pos+600])
