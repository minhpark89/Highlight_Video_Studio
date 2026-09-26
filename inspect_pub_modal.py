import os, json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# Let's inspect modal-publish-reel and how it is opened
pos_pub = text.find('id="modal-publish-reel"')
if pos_pub == -1:
    pos_pub = text.find('Xuất bản & Lên lịch Reels')
print("modal-publish-reel text pos:", pos_pub)
if pos_pub != -1:
    print(text[pos_pub-200:pos_pub+1800])
