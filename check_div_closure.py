from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where #content-area closes
pos_content_area = html.find('id="content-area"')
print("pos_content_area:", pos_content_area)

# Let's find where pane-groups is relative to #content-area
pos_pg = html.find('id="pane-groups"')
print("pos_pg:", pos_pg)

# Let's find all </div> between pos_content_area and pos_pg
sub = html[pos_content_area:pos_pg]
div_opens = len(re.findall(r'<div', sub))
div_closes = len(re.findall(r'</div', sub))
print(f"Between content-area and pane-groups: div opens = {div_opens}, div closes = {div_closes}")
