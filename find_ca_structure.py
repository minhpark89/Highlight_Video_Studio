from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's find where <div id="content-area"> is
pos_ca = html.find('id="content-area"')
print("pos_ca:", pos_ca)

# Let's find where </main> is
pos_main_end = html.find('</main>')
print("pos_main_end:", pos_main_end)

# Let's inspect all section tags inside <main>
sub = html[pos_ca:pos_main_end]
for m in re.finditer(r'<section\s+id="([^"]+)"', sub):
    print(f"Section {m.group(1)} at pos {pos_ca + m.start()}")

# Find the exact closing </div> of content-area
# Every section should be inside content-area, so the closing </div> of content-area should be right before <!-- Modals --> or right before </main>
pos_ca_close = html.rfind('</div>', 0, pos_main_end)
print("pos_ca_close:", pos_ca_close)
