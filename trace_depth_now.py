from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where #content-area closes
pos_ca = html.find('id="content-area"')
pos_pg = html.find('id="pane-groups"')

print(f"Content-area opens at {pos_ca}, pane-groups at {pos_pg}")

# Find where </main> is
pos_main = html.find('</main>')

# Let's trace all <div> and </div> from pos_ca to pos_main
sub = html[pos_ca:pos_main]
depth = 0
for m in re.finditer(r'<\/?div\b[^>]*>', sub):
    tag = m.group(0)
    pos = pos_ca + m.start()
    if tag.startswith('</div'):
        depth -= 1
        if depth == 0:
            print(f"Depth hit 0 at {pos}!")
            print("Snippet around close:")
            print(html[pos-100:pos+100])
    elif not tag.endswith('/>'):
        depth += 1

print(f"Final depth at </main>: {depth}")
