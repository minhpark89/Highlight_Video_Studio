import os, json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# Check openAssignSingleTokenModal
pos = text.find("function openAssignSingleTokenModal")
print("openAssignSingleTokenModal:\n", text[pos:pos+1000])
