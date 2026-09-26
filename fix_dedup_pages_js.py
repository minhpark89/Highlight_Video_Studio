import os, json, re, shutil
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"
INDEX_ALT_PATH = BASE_DIR / "web" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# Xoá khai báo trùng let cachedPagesList và let globalTokensCatalog ở đoạn cũ
old_decl = """  // ================= TOKEN & PAGE MANAGEMENT =================
  let cachedPagesList = [];
  let globalTokensCatalog = [];"""

replacement_decl = """  // ================= TOKEN & PAGE MANAGEMENT (SHARED REFS) ================="""

if old_decl in text:
    text = text.replace(old_decl, replacement_decl)
    print("Replaced old_decl successfully!")
else:
    print("Trying regex replace for duplicate cachedPagesList declaration...")
    text = re.sub(r'let\s+cachedPagesList\s*=\s*\[\];\s*let\s+globalTokensCatalog\s*=\s*\[\];', '// [Deduplicated declarations]', text, count=1)

with open(TEMPLATE_PATH, "w", encoding="utf-8") as f:
    f.write(text)
if INDEX_ALT_PATH.exists():
    with open(INDEX_ALT_PATH, "w", encoding="utf-8") as f:
        f.write(text)

print("Saved deduplicated index.html")
