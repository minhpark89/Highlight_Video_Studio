from pathlib import Path
import re

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where #content-area is opened and where each section is
pos_ca = html.find('id="content-area"')
pos_sett = html.find('id="pane-settings"')
pos_web = html.find('id="pane-website"')

print("content-area pos:", pos_ca)
print("pane-settings pos:", pos_sett)
print("pane-website pos:", pos_web)

# In previous edits, how was the gap for pane-groups fixed?
# Let's check git diff or check the hierarchy
# Look for any display: flex or margin-top or empty divs inside content-area
print("\n--- 500 chars before pane-settings ---")
print(html[pos_sett-500:pos_sett])

print("\n--- 500 chars before pane-website ---")
print(html[pos_web-500:pos_web])
