import os, json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# Let's inspect where the leaked form is inside pane-pages or after it
pos = text.find("Cơ chế phát video từ kho")
print("Position of 'Cơ chế phát video từ kho':", pos)

# Find surrounding block
p_start = text.rfind("<div", 0, pos - 150)
p_end = text.find("</div>", pos + 300)
# Let's see what is enclosing this
print("--- Surrounding 1000 chars ---")
print(text[pos-300:pos+700])
