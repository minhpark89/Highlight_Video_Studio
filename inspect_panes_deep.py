with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
# Look for class="tab-pane" or id="pane-
panes = re.findall(r'<div[^>]*class="[^"]*tab-pane[^"]*"[^>]*id="([^"]+)"', text)
if not panes:
    panes = re.findall(r'<section[^>]*id="([^"]+)"', text)
if not panes:
    panes = re.findall(r'id="(pane-[^"]+)"', text)
print("Panes:", panes)
