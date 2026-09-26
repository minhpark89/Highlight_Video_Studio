from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where #content-area closes
pos_ca = html.find('id="content-area"')
pos_pg = html.find('id="pane-groups"')
pos_pp = html.find('id="pane-posts"')

print(f"ca: {pos_ca}, pg: {pos_pg}, pp: {pos_pp}")

# Find where </main> is
pos_main_end = html.find('</main>')
print("main_end:", pos_main_end)

# Let's see what is right after pane-website or pane-settings (the other panes inside content-area)
pos_pw = html.find('id="pane-website"')
pos_pw_end = html.find('</section>', pos_pw)
print("pos_pw_end:", pos_pw_end)
print("Text after pane-website:", html[pos_pw_end:pos_pw_end+200])
