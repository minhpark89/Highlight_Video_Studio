from pathlib import Path
import re

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where pane-website and pane-settings are located
pos_ca = html.find('id="content-area"')
pos_ca_close = html.rfind('</div><!-- end content-area -->')
if pos_ca_close == -1:
    pos_ca_close = html.find('</main>')

pos_sett = html.find('id="pane-settings"')
pos_web = html.find('id="pane-website"')

print("content-area start:", pos_ca)
print("pane-settings:", pos_sett)
print("pane-website:", pos_web)
print("main tag:", pos_ca_close)

# What are the parents of pane-settings and pane-website?
# Print 300 chars before pane-settings
print("\n--- 300 chars before pane-settings ---\n", html[pos_sett-300:pos_sett])

# Print 300 chars before pane-website
print("\n--- 300 chars before pane-website ---\n", html[pos_web-300:pos_web])
