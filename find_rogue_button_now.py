import os, json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

pos_h = text.find("Hỗ trợ Hashtags")
print("Position:", pos_h)
if pos_h != -1:
    print(text[pos_h-100:pos_h+1500])
