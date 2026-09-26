from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect the switchTabs in index.html
pos1 = html.find('window.switchTab = function')
pos2 = html.find('window.switchTab = function', pos1 + 30)
print(f"Pos 1: {pos1}, Pos 2: {pos2}")

# Let's inspect Pos 1 (in head)
pos1_end = html.find('};', pos1)
print("=== POS 1 (HEAD) ===")
print(html[pos1:pos1_end+2])

# Let's inspect Pos 2 (in body)
if pos2 != -1:
    pos2_end = html.find('};', pos2)
    print("\n=== POS 2 (BODY) ===")
    print(html[pos2:pos2_end+2])
