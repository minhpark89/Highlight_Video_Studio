from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect the layout of <main id="main"> and padding/margin of .pane
pos_main = html.find('<main id="main">')
pos_header = html.find('</header>', pos_main)
print(html[pos_main:pos_header+9])

# Check what is immediately after </header>
print("=== AFTER HEADER ===")
print(html[pos_header+9:pos_header+600])
