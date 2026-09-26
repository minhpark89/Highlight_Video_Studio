from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect the lazy loader in switchTab for pane-tokens
pos = html.find("if (paneId === 'pane-tokens'")
print("pos:", pos)
if pos != -1:
    print(html[pos-100:pos+300])

# Let's see what loadTokensOnly looks like in index.html
pos_to = html.find("async function loadTokensOnly()")
print("pos_to:", pos_to)
if pos_to != -1:
    print(html[pos_to:pos_to+800])
