import os
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("<!-- Box 2: Tự nhiên hóa & Giới hạn an toàn -->")
print("pos of Box 2:", pos)
if pos != -1:
    # Check 1500 chars around Box 2
    print(text[pos:pos+2500])
