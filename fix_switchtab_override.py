from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's inspect the two switchTab functions in index.html:
# pos1 is in head (line ~19196)
# pos2 is in body (line ~79061)

pos1 = html.find('window.switchTab = function')
pos2 = html.find('window.switchTab = function', pos1 + 30)

print(f"Pos 1: {pos1}, Pos 2: {pos2}")

# Check what pos2 does and replace it or merge it
pos2_end = html.find('};\n', pos2)
if pos2_end == -1: pos2_end = html.find('};', pos2)
print("pos2 code snippet:")
print(html[pos2:pos2_end+2])

# Let's check where loadLoHaGroups is called
# In pos2, it does NOT call loadLoHaGroups at all! That's why clicking Tab Nhóm Trang didn't trigger loadLoHaGroups!
