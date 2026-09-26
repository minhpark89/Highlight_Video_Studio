from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where id="content-area" starts and where all sections are
pos_ca = html.find('id="content-area"')

import re
matches = list(re.finditer(r'<section\s+id=[\"\']([^\"\']+)[\"\']', html))
for m in matches:
    name = m.group(1)
    pos = m.start()
    print(f"Section {name} at {pos} (ca_pos: {pos_ca}, diff: {pos - pos_ca})")

# Where does content-area close?
# Let's find </main> or </div> before modals or scripts
pos_modals = html.find('<!-- MODALS -->')
if pos_modals == -1: pos_modals = html.find('class="modal"')
print("Modals at:", pos_modals)

# Let's see what is right after pane-website
pos_web = html.find('id="pane-website"')
pos_web_end = html.find('</section>', pos_web)
print("After pane-website:\n", html[pos_web_end:pos_web_end+500])
