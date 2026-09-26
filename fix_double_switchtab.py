from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect the two switchTabs:
# 1. In head (starts around pos 19196)
# 2. In body (starts around pos 79061)

pos1 = html.find('window.switchTab = function')
pos2 = html.find('window.switchTab = function', pos1 + 30)

print(f"Pos 1: {pos1}, Pos 2: {pos2}")

# Let's look at the body switchTab (pos2)
pos2_end = html.find('};\n', pos2)
if pos2_end == -1: pos2_end = html.find('};', pos2)
body_switch = html[pos2:pos2_end+2]

print("Body switchTab ends at:", pos2_end)
