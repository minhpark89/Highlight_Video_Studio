import json
import re

with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Check all panes
panes = re.findall(r'<div[^>]*id="(pane-[^"]+)"', html)
print("Panes currently present in HTML:")
for p in set(panes):
    print(" -", p)

# Check all button onclick switchTab
tabs = re.findall(r'switchTab\(\'([^\']+)\'', html)
print("\nTabs in switchTab calls:")
for t in set(tabs):
    print(" -", t)
