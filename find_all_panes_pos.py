from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where id="content-area" starts and ends
pos_ca = html.find('id="content-area"')
print("content-area start:", pos_ca)

# Find all <section id="pane-...
import re
sections = re.findall(r'<section\s+id=[\"\'](pane-[a-zA-Z0-9_-]+)[\"\']', html)
print("All panes found in index.html:", sections)

for s in sections:
    pos_s = html.find(f'id="{s}"')
    print(f"  Pane {s} at position {pos_s} (inside content-area? {pos_s > pos_ca})")
