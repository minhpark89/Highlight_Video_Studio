import os
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("<!-- Box 2: Tự nhiên hóa & Giới hạn an toàn -->")
print("Box 2 pos:", pos)
if pos != -1:
    # Let's inspect 4000 characters from pos
    snippet = text[pos:pos+4000]
    print("=== SNIPPET ===")
    print(snippet)
    print("=== END SNIPPET ===")
    with open(BASE_DIR / "box2_full_leak.html", "w", encoding="utf-8") as out:
        out.write(snippet)
