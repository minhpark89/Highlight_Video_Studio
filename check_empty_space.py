from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where #main and #pane-groups are located
pos_main = html.find('<main id="main">')
pos_pg = html.find('id="pane-groups"')
print("pos_main:", pos_main)
print("pos_pg:", pos_pg)

# Let's see what is inside <main id="main"> between pos_main and pos_pg
sub = html[pos_main:pos_pg]
print("Content length between main and pane-groups:", len(sub))

# Check sections in sub
sections = re.findall(r'<section[^>]*id="([^"]+)"[^>]*class="([^"]+)"', sub)
print("Sections found before pane-groups:")
for s_id, s_cls in sections:
    print(f" - #{s_id} (class='{s_cls}')")
