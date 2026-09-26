from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where #pane-groups and #pane-posts are placed.
# In diag_gap.py:
# Layout Info:
# paneRect top: 183.859375
# caRect top: 64, height: 119.859375, bottom: 183.859375
# This proves pane-groups is rendering OUTSIDE #content-area, beneath #content-area!
# Because #content-area closes BEFORE pane-groups!
# When pane-groups is active, #content-area has height 119px (from empty padding), and pane-groups sits BELOW it!

print("Let's check where pane-groups is currently placed in html:")
pos_pg = html.find('id="pane-groups"')
pos_ca = html.find('id="content-area"')
print("pos_ca:", pos_ca, "pos_pg:", pos_pg)

# Find where </main> is
pos_main_end = html.find('</main>')
print("pos_main_end:", pos_main_end)
