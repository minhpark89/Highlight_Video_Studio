from pathlib import Path
import re

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where #content-area is opened and where it is closed
pos_ca = html.find('id="content-area"')
print("content-area pos:", pos_ca)

# Find pane-website and pane-settings
pos_sett = html.find('id="pane-settings"')
pos_web = html.find('id="pane-website"')
pos_gal = html.find('id="pane-gallery"')
pos_jobs = html.find('id="pane-jobs"')

print("pane-jobs pos:", pos_jobs)
print("pane-gallery pos:", pos_gal)
print("pane-settings pos:", pos_sett)
print("pane-website pos:", pos_web)

# Check closing divs between content-area and pane-settings
sub = html[pos_ca:pos_sett]
# Let's check why pane-settings and pane-website show at bottom with huge empty space
print("Snippet 200 chars before pane-settings:\n", html[pos_sett-300:pos_sett])
