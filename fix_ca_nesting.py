from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where #content-area closes
pos_ca = html.find('id="content-area"')
pos_pg = html.find('id="pane-groups"')

print(f"Content-area opens at {pos_ca}, pane-groups at {pos_pg}")

# Let's trace all opening and closing tags between pos_ca and pos_pg
# We want pane-groups and pane-posts to be INSIDE #content-area, right after the last pane (pane-website), BEFORE </div> of #content-area!
pos_pw = html.find('id="pane-website"')
pos_pw_end = html.find('</section>', pos_pw) + 10
print(f"pane-website ends at {pos_pw_end}")

# Let's check what is right after pos_pw_end
print("Snippet after pane-website:")
print(html[pos_pw_end:pos_pw_end+300])
