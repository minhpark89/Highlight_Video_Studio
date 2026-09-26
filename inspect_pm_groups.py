import os, json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
with open(BASE_DIR / "src" / "publisher" / "page_manager.py", "r", encoding="utf-8") as f:
    text = f.read()

print("page_manager.py group methods:")
for line in text.splitlines():
    if "group" in line.lower() or "def " in line:
        print("  ", line)

print("\nFull group methods code:")
pos = text.find("def list_groups")
if pos != -1:
    print(text[pos:])
