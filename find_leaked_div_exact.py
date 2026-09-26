import os, json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# Let's inspect where "Cơ chế phát video từ kho" is and how it was placed
pos = text.find("Cơ chế phát video từ kho")
print("Position of 'Cơ chế phát video từ kho':", pos)

# Find the start and end of this obsolete block
start = text.rfind("<div", 0, pos - 150)
# Look back further to see the parent card/form
start_card = text.rfind('<div class="card"', 0, pos)
if start_card == -1:
    start_card = text.rfind('<div class="panel"', 0, pos)
if start_card == -1:
    start_card = text.rfind('<section', 0, pos)

print("start_card pos:", start_card)
print("Snippet from start_card:")
print(text[start_card:pos+400])
