from pathlib import Path
import re

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where #content-area is opened and where it is closed
pos_ca = html.find('id="content-area"')
print("content-area pos:", pos_ca)

# Find pane-website and pane-settings
pos_sett = html.find('id="pane-settings"')
pos_web = html.find('id="pane-website"')

print("pane-settings pos:", pos_sett)
print("pane-website pos:", pos_web)

# Let's inspect pane-studio
pos_studio = html.find('id="pane-studio"')
print("pane-studio pos:", pos_studio)

# Check all child elements directly inside content-area
print("\nFirst 1000 chars of content-area:\n", html[pos_ca:pos_ca+1000])
