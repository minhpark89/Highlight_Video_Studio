import os, json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# Let's inspect where "Cơ chế phát video từ kho" and "Curiosity Hook" are coming from
pos = text.find("Cơ chế phát video")
if pos == -1:
    pos = text.find("Round Robin")
print("Found position:", pos)
if pos != -1:
    print(text[pos-400:pos+800])
