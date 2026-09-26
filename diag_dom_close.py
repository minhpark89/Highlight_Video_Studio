from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where id="content-area" starts and where all sections are
pos_ca = html.find('id="content-area"')
print("content-area pos:", pos_ca)

import re
matches = list(re.finditer(r'<section\s+id=[\"\']([^\"\']+)[\"\']', html))
for m in matches:
    name = m.group(1)
    pos = m.start()
    print(f"Section {name} at pos {pos}")

# Where does content-area close?
# Let's check div depth from pos_ca
pos = pos_ca
depth = 0
for m in re.finditer(r'(<div[^>]*>|</div>)', html[pos_ca:]):
    tag = m.group(1)
    if tag.startswith('<div'):
        depth += 1
    else:
        depth -= 1
        if depth == 0:
            print("content-area closed at absolute pos:", pos_ca + m.end())
            # Let's print 200 chars around this closing tag
            close_pos = pos_ca + m.start()
            print("Closing snippet:\n", html[close_pos-100:close_pos+200])
            break
