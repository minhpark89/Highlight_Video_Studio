import os, re
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# Let's search for "Cơ chế phát video từ kho"
pos = text.find("Cơ chế phát video từ kho")
print("Position:", pos)
if pos != -1:
    # Look back to find where this rogue form starts
    p_start = text.rfind("<div class=\"card\"", 0, pos)
    if p_start == -1:
        p_start = text.rfind("<div", 0, pos - 200)
    p_end = text.find("</section>", pos)
    print("p_start:", p_start, "p_end:", p_end)
    print("=== ROGUE BLOCK CONTENT ===")
    print(text[p_start:pos+600])
    print("=== END ===")
