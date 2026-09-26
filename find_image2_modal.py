import os, re
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# Find "Hỗ trợ Hashtags"
pos = text.find("Hỗ trợ Hashtags")
print("Position of 'Hỗ trợ Hashtags':", pos)
if pos != -1:
    # Look back to find what modal or container this belongs to
    p_start = text.rfind("<div", 0, pos - 300)
    p_modal = text.rfind("id=\"modal-", 0, pos)
    p_sec = text.rfind("<section", 0, pos)
    print("p_modal:", p_modal, "p_sec:", p_sec)
    if p_modal != -1:
        print("Modal id near:", text[p_modal:p_modal+40])
    print("=== SNIPPET BEFORE ===")
    print(text[pos-400:pos])
    print("=== SNIPPET AFTER ===")
    print(text[pos:pos+1000])
