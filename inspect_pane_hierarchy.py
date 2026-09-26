from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where #pane-groups starts and what is right above it
pos_pg = html.find('id="pane-groups"')
print("Index of pane-groups:", pos_pg)
print("=== 400 chars before pane-groups ===")
print(html[pos_pg-400:pos_pg])

# Let's check all sections inside #content-area
pos_ca = html.find('id="content-area"')
sub = html[pos_ca:pos_pg+500]

sections = re.findall(r'<section[^>]+id="([^"]+)"[^>]*>', sub)
print("Sections between content-area and pane-groups:")
for s in sections:
    print(" -", s)
