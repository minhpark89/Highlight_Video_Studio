from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's see what is inside pane-tokens currently
pos_start = html.find('id="pane-tokens"')
pos_end = html.find('</section>', pos_start)

print("Current pane-tokens length:", pos_end - pos_start)
print(html[pos_start:pos_end+10])
