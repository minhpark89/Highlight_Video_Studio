import json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
INDEX_PATH = BASE_DIR / "web" / "templates" / "index.html"

html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect the switchTab in <head>
pos_sw = html.find('window.switchTab = function')
pos_end_sw = html.find('};', pos_sw)
print(html[pos_sw:pos_end_sw+2])
