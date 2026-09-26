import os
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("Hỗ trợ Hashtags")
print("Position:", pos)
if pos != -1:
    # Look back 500 chars and forward 800 chars
    start = max(0, pos - 500)
    end = min(len(text), pos + 800)
    print("=== SNIPPET ===")
    print(text[start:end])
    print("=== END ===")
