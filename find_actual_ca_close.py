from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where #content-area starts and ends
pos_ca = html.find('id="content-area"')
print("pos_ca:", pos_ca)

# Find where </main> is
pos_main = html.find('</main>')
print("pos_main:", pos_main)

# Between pos_ca and pos_main, find all <div and </div
sub = html[pos_ca:pos_main]
div_depth = 0
for m in re.finditer(r'<\/?div\b[^>]*>', sub):
    tag = m.group(0)
    pos = pos_ca + m.start()
    if tag.startswith('</div'):
        div_depth -= 1
        if div_depth == 0:
            print(f"Content-area closed at pos {pos}!")
            print("Snippet around close:")
            print(html[pos-100:pos+100])
            break
    elif not tag.endswith('/>'):
        div_depth += 1

print("Final depth if not broken:", div_depth)
