from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where #content-area opens and where it closes
pos_ca = html.find('id="content-area"')
print("pos_ca:", pos_ca)

# Find where the other sections are (pane-studio, pane-research, etc.)
# We want pane-groups, pane-posts to be directly inside #content-area, right after pane-website, and before the closing </div> of content-area.
# Let's trace where #content-area closes currently.
pos_pw = html.find('id="pane-website"')
pos_pw_end = html.find('</section>', pos_pw) + 10

# Let's inspect the next 500 characters after pane-website
print("After pane-website:")
print(html[pos_pw_end:pos_pw_end+500])
