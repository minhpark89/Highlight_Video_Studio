from pathlib import Path
import re

html_tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
text = html_tmpl.read_text(encoding="utf-8")

# Let's inspect loadTokensAndPages around line 180100
pos = text.find("async function loadTokensAndPages()")
pos_end = text.find("function renderFilteredPages", pos)
print("=== loadTokensAndPages ===")
print(text[pos:pos+2500])
