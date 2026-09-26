import os, json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# Let's inspect where "Cơ chế phát video" is in index.html
pos = text.find("Cơ chế phát video")
if pos != -1:
    print("Found 'Cơ chế phát video' at index:", pos)
    # Print 500 chars before and 800 chars after
    start = max(0, pos - 500)
    end = min(len(text), pos + 1000)
    print("=== SNIPPET ===")
    print(text[start:end])
    print("=== END SNIPPET ===")
