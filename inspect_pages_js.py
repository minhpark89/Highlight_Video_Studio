import os, json, re
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    html = f.read()

# Inspect loadTokensAndPages in JS
pos_fn = html.find("async function loadTokensAndPages()")
if pos_fn != -1:
    print("Found loadTokensAndPages at", pos_fn)
    print(html[pos_fn:pos_fn+3000])
else:
    print("loadTokensAndPages not found!")
