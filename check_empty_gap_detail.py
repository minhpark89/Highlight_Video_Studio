from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect CSS for main, content, pane, etc.
pos_main = html.find('#main {')
print(html[pos_main:pos_main+600])

pos_pane = html.find('.pane {')
print(html[pos_pane:pos_pane+400])

# Check what wraps the panes
pos_main_tag = html.find('<main id="main">')
print(html[pos_main_tag:pos_main_tag+1200])
