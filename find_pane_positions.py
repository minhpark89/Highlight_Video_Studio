with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Let's find where panes start and end
pos_main = text.find('<main id="main">')
print("pos_main:", pos_main)

# Let's find all id="pane-..."
import re
for m in re.finditer(r'<div[^>]*id="(pane-[^"]+)"', text):
    print(f"Pane: {m.group(1)} at pos {m.start()}")
