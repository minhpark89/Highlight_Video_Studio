import os
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# Let's find "Xác nhận Lên Lịch (Schedule)"
pos = text.find("Xác nhận Lên Lịch (Schedule)")
print("Position:", pos)
if pos != -1:
    # Look back to see what opened this block
    p_start = text.rfind("<div", 0, pos - 1500)
    print("Start around:", p_start)
    print("=== START SNIPPET ===")
    print(text[pos-1200:pos-800])
    print("=== END SNIPPET ===")
    print(text[pos:pos+400])
