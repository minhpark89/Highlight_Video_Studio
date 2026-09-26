from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect pane-tokens in html
pos = html.find('id="pane-tokens"')
pos_end = html.find('</section>', pos)
print("pane-tokens length:", pos_end - pos)

# Check loha-token-group-pills in html
print("Has loha-token-group-pills:", 'loha-token-group-pills' in html)

# Let's see what is inside pane-tokens
print(html[pos:pos+2000])
