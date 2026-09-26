from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect line 38650-38680
pos = 38657
print("=== Around 38657 ===")
print(html[pos-100:pos+150])

# Trace pane-studio from its start
pos_ps = html.find('id="pane-studio"')
pos_ps_end = html.find('</section>', pos_ps)
print("pane-studio start:", pos_ps, "end:", pos_ps_end)

# Let's see all sections in html
for m in re.finditer(r'<section\s+id="([^"]+)"', html):
    print(f"Section {m.group(1)}: start={m.start()}")
