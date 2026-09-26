import json
import re

with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Let's locate all panes
matches = list(re.finditer(r'<div\s+id="(pane-[^"]+)"', text))
print("Found panes:")
for m in matches:
    print(f"Pane {m.group(1)} at pos {m.start()}")
