from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's inspect where #content-area begins and what follows
pos_ca = html.find('id="content-area"')
print("pos_ca:", pos_ca)

# Let's inspect all <section tags after pos_ca
import re
sections = list(re.finditer(r'<section\s+id="([^"]+)"', html[pos_ca:]))
for s in sections:
    print(f"Section {s.group(1)} at {pos_ca + s.start()}")

# Let's check where the closing </div> of content-area is
# Where was content-area closed?
# Let's search for the closing </main>
pos_main_close = html.find('</main>')
print("pos_main_close:", pos_main_close)

# Between pos_ca and pos_main_close, let's see why pane-groups had paneParentId = 'main'
# That means there is a </div> before pane-groups that closed content-area!
pos_pg = html.find('id="pane-groups"')
print("pos_pg:", pos_pg)
sub = html[pos_ca:pos_pg]
opens = len(re.findall(r'<div\b', sub))
closes = len(re.findall(r'</div\b', sub))
print(f"Between content-area and pane-groups: <div={opens}, </div={closes}")
