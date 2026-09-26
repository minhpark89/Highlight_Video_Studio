from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where nav buttons are defined
pos = html.find('id="sidebar"')
pos_end = html.find('</aside>', pos)
print("=== Current Sidebar ===")
print(html[pos:pos_end+8])
