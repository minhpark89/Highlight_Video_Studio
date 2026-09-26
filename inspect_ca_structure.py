from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where id="content-area" starts and ends
pos_ca = html.find('id="content-area"')
pos_pg = html.find('id="pane-groups"')
print("pos_ca:", pos_ca)
print("pos_pg:", pos_pg)

# Let's find all closing tags </div> between pos_ca and pos_pg
sub = html[pos_ca:pos_pg]
print("Snippet before pos_pg (200 chars):")
print(html[pos_pg-200:pos_pg])
