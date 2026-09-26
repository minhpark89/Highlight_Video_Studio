import os, json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

pos_m = text.find('id="modal-add-group"')
if pos_m != -1:
    print(text[pos_m:pos_m+3000])
else:
    print("modal-add-group not found")
