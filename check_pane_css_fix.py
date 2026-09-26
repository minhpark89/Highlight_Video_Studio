from pathlib import Path
import re

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's check where the content-area opening tag is
pos_ca = html.find('id="content-area"')
print("content-area pos:", pos_ca)

# Let's inspect CSS for .pane
pos_css = html.find('.pane {')
print("pane css pos:", pos_css)
if pos_css != -1:
    print(html[pos_css:pos_css+300])

pos_pane_act = html.find('.pane.active')
print("pane active css pos:", pos_pane_act)
if pos_pane_act != -1:
    print(html[pos_pane_act:pos_pane_act+300])
