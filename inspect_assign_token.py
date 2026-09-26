import os, json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("openAssignSingleTokenModal")
print("openAssignSingleTokenModal definition:")
print(text[pos:pos+1200])
