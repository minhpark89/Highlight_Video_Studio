import os, json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# Let's inspect modal-add-group and save group logic in index.html
pos = text.find('id="modal-add-group"')
print("modal-add-group pos:", pos)
if pos != -1:
    print(text[pos:pos+3500])

pos_fn = text.find("function saveAddGroup")
if pos_fn == -1:
    pos_fn = text.find("function createGroup")
if pos_fn == -1:
    pos_fn = text.find("async function saveGroup")
print("save group fn pos:", pos_fn)
if pos_fn != -1:
    print(text[pos_fn:pos_fn+1500])
