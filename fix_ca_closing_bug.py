from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where #content-area is and how it wraps panes
pos_ca = html.find('id="content-area"')
print("pos_ca:", pos_ca)

# Let's find where pane-groups is
pos_pg = html.find('id="pane-groups"')
print("pos_pg:", pos_pg)

# In diag_exact_gap.py earlier:
# caRect top: 64, height: 674, bottom: 738
# paneTop: 738
# Why did ca have height 674?
# Because <div id="content-area"> ended BEFORE pane-groups!
# Let's find WHERE <div id="content-area"> was closed.
