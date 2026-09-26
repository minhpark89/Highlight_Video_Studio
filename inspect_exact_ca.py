from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect line 38650-38670
pos = 38657
print("=== Around 38657 ===")
print(html[pos-100:pos+150])

# Let's see why content-area closed early
# Check <div id="content-area"> tag
pos_ca = html.find('id="content-area"')
print("pos_ca:", pos_ca)

# Check all sections inside html
sections = list(re.finditer(r'<section\s+id="([^"]+)"', html))
for s in sections:
    print(f"Section {s.group(1)} at {s.start()}")
