from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where #pane-groups and #pane-posts are placed.
# We found:
# pos_ca = html.find('id="content-area"')
# In previous run:
# Content-area starts at 26404
# Pane-groups at 72762
# Modals at 231873
# Closing </div> of content-area at: 229744 ? Wait, let's verify where <div id="content-area"> actually closes!

pos_ca = html.find('id="content-area"')
print("pos_ca:", pos_ca)

# Let's trace all <div> and </div> after pos_ca
pos = pos_ca
depth = 0
in_ca = True
while pos < len(html):
    m = re.search(r'<\/?div\b[^>]*>', html[pos:])
    if not m:
        break
    tag = m.group(0)
    tag_pos = pos + m.start()
    if tag.startswith('</div'):
        depth -= 1
        if depth == 0:
            print(f"content-area CLOSES at index {tag_pos}!")
            print("Snippet around close:")
            print(html[tag_pos-100:tag_pos+100])
            break
    else:
        # ignore self-closing
        if not tag.endswith('/>'):
            depth += 1
    pos = tag_pos + len(tag)
