from pathlib import Path
import re

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# 1. Check all section panes
panes = re.findall(r'<section\s+id=[\"\']([^\"\']+)[\"\']', html)
print("All panes in index.html:", panes)

# 2. Check sidebar nav items
nav_items = re.findall(r'data-pane=[\"\']([^\"\']+)[\"\']', html)
print("Sidebar nav items:", nav_items)

# 3. Check where content-area is
pos_ca = html.find('id="content-area"')
print("content-area start pos:", pos_ca)

for p in panes:
    pos = html.find(f'id="{p}"')
    print(f"  Pane '{p}': pos {pos}")
