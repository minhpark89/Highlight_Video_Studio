from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where pane-tokens is located in html
pos_t = html.find('id="pane-tokens"')
pos_end_t = html.find('</section>', pos_t)

print("pane-tokens length:", pos_end_t - pos_t)
print(html[pos_t:pos_t+500])
