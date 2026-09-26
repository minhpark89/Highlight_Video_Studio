from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect the lazy loader in switchTab in head
pos_sw = html.find('window.switchTab = function')
pos_end_sw = html.find('};', pos_sw)
print("=== Head switchTab ===")
print(html[pos_sw:pos_end_sw+2])

# Let's inspect switchTab in body
pos_b_sw = html.find('window.switchTab = function', pos_sw + 30)
if pos_b_sw != -1:
    pos_b_end = html.find('};', pos_b_sw)
    print("\n=== Body switchTab ===")
    print(html[pos_b_sw:pos_b_end+2])
