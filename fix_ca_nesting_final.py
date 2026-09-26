from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where #content-area opens and where it closes
pos_ca = html.find('id="content-area"')
print("pos_ca:", pos_ca)

# Find where the other sections are (pane-studio, pane-research, etc.)
sections = list(re.finditer(r'<section\s+id="([^"]+)"', html))
for s in sections:
    print(f"Section {s.group(1)} at {s.start()}")

# Let's find the closing </div> of content-area
# Look at all </div> tags
# Where was content-area closed in the original template?
# Let's inspect the end of pane-website or modals
pos_modals = html.find('<!-- Modals')
if pos_modals == -1: pos_modals = html.find('id="modal-')

print("pos_modals:", pos_modals)
