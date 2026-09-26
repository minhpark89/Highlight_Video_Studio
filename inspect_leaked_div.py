import os, json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("Cơ chế phát video")
print("Found position of leaked form:", pos)
if pos != -1:
    # Find start of the block containing this form
    p_start = text.rfind("<div", 0, pos - 200)
    print("Around p_start:\n", text[pos-300:pos+500])
