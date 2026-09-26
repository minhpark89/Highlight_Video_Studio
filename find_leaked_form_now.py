import os
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("Hỗ trợ Hashtags")
print("Position of 'Hỗ trợ Hashtags':", pos)
if pos != -1:
    # Look back 800 chars
    start = max(0, pos - 800)
    end = min(len(text), pos + 1200)
    print("=== SNIPPET ===")
    print(text[start:end])
    print("=== END ===")
