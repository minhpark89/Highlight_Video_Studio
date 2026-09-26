from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect CSS for #content-area and .pane
pos = html.find('#content-area {')
print(html[pos:pos+400])

# Check where pane-groups is in html
pos_pg = html.find('id="pane-groups"')
print("pane-groups index:", pos_pg)
# Check 300 chars before
print(html[pos_pg-300:pos_pg+100])
