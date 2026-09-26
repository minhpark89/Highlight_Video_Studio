import json
from pathlib import Path

# Let's inspect D:\Highlight_Video_Studio\web\templates\index.html around pane-tokens
with open(r"D:\Highlight_Video_Studio\web\templates\index.html", "r", encoding="utf-8") as f:
    text = f.read()

pos_pt = text.find('id="pane-tokens"')
pos_end_pt = text.find('</section>', pos_pt)
print("pane-tokens length:", pos_end_pt - pos_pt)
print(text[pos_pt:pos_pt+1200])
