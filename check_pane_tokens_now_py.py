import json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
html = (BASE_DIR / "web" / "templates" / "index.html").read_text(encoding="utf-8")

pos = html.find('id="pane-tokens"')
pos_end = html.find('</section>', pos)
print("pane-tokens length:", pos_end - pos)
print(html[pos:pos+1500])
