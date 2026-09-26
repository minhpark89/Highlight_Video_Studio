from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect line 38640-38680 to see why depth hit 0
pos = 38657
print("=== Around 38657 ===")
print(html[pos-150:pos+200])
