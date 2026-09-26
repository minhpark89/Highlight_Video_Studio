from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where #content-area ends and where #pane-groups begins
pos_pg = html.find('id="pane-groups"')
pos_before = html.rfind('</section>', 0, pos_pg)
print(html[pos_before:pos_pg+30])

# Check if there is an unclosed tag or if pane-groups is outside #content-area
pos_ca = html.find('id="content-area"')
pos_end_ca = html.find('</div>\n    <!-- Modals', pos_ca)
if pos_end_ca == -1: pos_end_ca = html.find('id="modal-', pos_ca)
print("pos_ca:", pos_ca, "pos_pg:", pos_pg, "pos_end_ca:", pos_end_ca)
