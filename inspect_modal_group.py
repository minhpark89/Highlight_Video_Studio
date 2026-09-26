import os, json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# Let's inspect modal-add-group
pos = text.find('id="modal-add-group"')
print("modal-add-group pos:", pos)
if pos != -1:
    print(text[pos:pos+2000])
