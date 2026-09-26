from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where #content-area closes
pos_ca = html.find('id="content-area"')
print("Content-area at:", pos_ca)

# Find where </main> is
pos_main_end = html.find('</main>')
print("Main ends at:", pos_main_end)

# Let's find all closing </div> tags between pos_ca and pos_main_end
sub = html[pos_ca:pos_main_end]
div_depth = 0
last_zero = -1
for m in re.finditer(r'<\/?div\b[^>]*>', sub):
    tag = m.group(0)
    if tag.startswith('</div'):
        div_depth -= 1
        if div_depth == 0:
            print(f"Depth hit 0 at {pos_ca + m.start()}")
            last_zero = pos_ca + m.start()
    elif not tag.endswith('/>'):
        div_depth += 1

print("Final depth:", div_depth)
print("Snippet around last_zero:")
print(html[last_zero-150:last_zero+150])
