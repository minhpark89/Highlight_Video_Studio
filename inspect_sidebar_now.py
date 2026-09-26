from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect sidebar in index.html
pos = html.find('id="sidebar"')
pos_end = html.find('</aside>', pos)
print(html[pos:pos_end+8])
