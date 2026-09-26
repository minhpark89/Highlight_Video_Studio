from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect CSS for #main, .content, etc.
# Look for #content or main padding
pos = html.find('padding: 24px 28px 60px;')
if pos != -1:
    print("Found padding rule around pos:", pos)
    print(html[pos-100:pos+200])

# Let's inspect where #content is or where panes are placed
pos_main = html.find('<main id="main">')
pos_first_pane = html.find('<section id="pane-', pos_main)
print("Between <main> and first pane:")
print(html[pos_main:pos_first_pane])
