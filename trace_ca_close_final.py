from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where #content-area opens
pos_ca = html.find('id="content-area"')
print("pos_ca:", pos_ca)

# Let's trace all <div> and </div> until we find where content-area actually closes
pos = pos_ca
depth = 0
ca_closed_at = -1
while pos < len(html):
    m = re.search(r'<\/?div\b[^>]*>', html[pos:])
    if not m:
        break
    tag = m.group(0)
    tag_pos = pos + m.start()
    if tag.startswith('</div'):
        depth -= 1
        if depth == 0:
            ca_closed_at = tag_pos
            break
    elif not tag.endswith('/>'):
        depth += 1
    pos = tag_pos + len(tag)

print(f"Content-area opened at {pos_ca} and CLOSED at {ca_closed_at}")
print("Snippet around ca_closed_at:")
print(html[ca_closed_at-150:ca_closed_at+150])
