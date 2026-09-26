from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect pane-tokens in html
pos_t = html.find('id="pane-tokens"')
pos_t_end = html.find('</section>', pos_t)
print(html[pos_t:pos_t+1500])
