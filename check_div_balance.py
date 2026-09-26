from pathlib import Path
import re

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's find why pane-website and pane-settings are shifted down.
# In earlier turns, pane-groups and pane-posts were moved inside #content-area,
# but what about pane-settings and pane-website?
# Where is #content-area closed?

pos_ca = html.find('id="content-area"')
print("content-area pos:", pos_ca)

# Let's find all closing </div> between pos_ca and pane-settings
pos_sett = html.find('id="pane-settings"')
pos_web = html.find('id="pane-website"')

snippet = html[pos_ca:pos_sett]
open_divs = len(re.findall(r'<div\b', snippet))
close_divs = len(re.findall(r'</div>', snippet))
print(f"Between content-area and pane-settings: open divs = {open_divs}, close divs = {close_divs}")
print(f"Difference (depth): {open_divs - close_divs}")
