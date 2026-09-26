from pathlib import Path
import re

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect loadTokensAndPages in index.html
pos = html.find('async function loadTokensAndPages')
pos_end = html.find('function renderPagination', pos)
print("=== loadTokensAndPages to renderPagination ===")
print(html[pos:pos+3000])
