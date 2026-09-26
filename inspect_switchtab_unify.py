from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect the two switchTabs:
pos1 = html.find('window.switchTab = function')
pos2 = html.find('window.switchTab = function', pos1 + 30)

print(f"Pos 1: {pos1}, Pos 2: {pos2}")

# Replace the second switchTab completely or unify it
pos2_end = html.find('};\n', pos2)
if pos2_end == -1: pos2_end = html.find('};', pos2)
print("Second switchTab length:", pos2_end - pos2)

# Also check sidebar labels
print("Sidebar snippet:")
pos_sb = html.find('id="sidebar"')
print(html[pos_sb:pos_sb+1200])
