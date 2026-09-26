from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where #content-area closes
pos_ca = html.find('id="content-area"')
pos_pg = html.find('id="pane-groups"')

# In diag_exact_gap.py:
# Layout Info: {'paneParentId': 'main', 'paneParentTag': 'MAIN', 'caChildren': ...}
# Notice paneParentId is 'main'! NOT 'content-area'!
# That means #content-area closed BEFORE pane-groups!
# When pane-groups is active, #content-area is ABOVE pane-groups!
# And #content-area takes 674px of empty height, pushing pane-groups down to 738px!

print("Content-area starts at:", pos_ca)
print("Pane-groups starts at:", pos_pg)

# Let's find the closing </div> of #content-area
# We need to trace from pos_ca
pos = pos_ca
depth = 0
ca_close_pos = -1

while pos < len(html):
    m = re.search(r'<\/?div\b[^>]*>', html[pos:])
    if not m:
        break
    tag = m.group(0)
    tag_pos = pos + m.start()
    if tag.startswith('</div'):
        depth -= 1
        if depth == 0:
            ca_close_pos = tag_pos
            break
    else:
        if not tag.endswith('/>'):
            depth += 1
    pos = tag_pos + len(tag)

print("Actual closing </div> of content-area is at:", ca_close_pos)
print("Snippet around ca_close_pos:")
print(html[ca_close_pos-200:ca_close_pos+200])
