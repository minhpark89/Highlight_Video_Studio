from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect pane-tokens in html
pos = html.find('id="pane-tokens"')
pos_end = html.find('</section>', pos)
print("pane-tokens length:", pos_end - pos)

with open(r"D:\Highlight_Video_Studio\pt_debug.txt", "w", encoding="utf-8") as out:
    out.write(html[pos:pos_end+10])

print("Wrote pt_debug.txt successfully!")
