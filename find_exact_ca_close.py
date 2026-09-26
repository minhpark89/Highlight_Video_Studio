from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where #content-area starts and ends
pos_ca = html.find('id="content-area"')
print("pos_ca:", pos_ca)

# Let's find where pane-groups and pane-posts currently are
pos_pg = html.find('id="pane-groups"')
pos_pp = html.find('id="pane-posts"')
print("pos_pg:", pos_pg)
print("pos_pp:", pos_pp)

# Let's find the closing </div> of content-area
# Look at all </div> between pos_ca and pos_pg
sub = html[pos_ca:pos_pg]
div_depth = 0
for m in re.finditer(r'<\/?div\b[^>]*>', sub):
    tag = m.group(0)
    if tag.startswith('</div'):
        div_depth -= 1
        if div_depth == 0:
            print(f"Content-area closed at pos {pos_ca + m.start()}!")
            print("Around close:", html[pos_ca+m.start()-100:pos_ca+m.start()+100])
    elif not tag.endswith('/>'):
        div_depth += 1

print("Final div depth before pane-groups:", div_depth)
