from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect CSS for .pane, .pane.active, and #main
pos = html.find('/* Panes */')
if pos == -1: pos = html.find('.pane {')
print(html[pos:pos+500])

# Check pane-research active
print("Occurrences of 'class=\"pane active\"':", [m.start() for m in re.finditer(r'class="pane active"', html)])
