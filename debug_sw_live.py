from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's inspect the two switchTabs
pos1 = html.find('window.switchTab = function')
pos2 = html.find('window.switchTab = function', pos1 + 30)

print(f"pos1: {pos1}, pos2: {pos2}")
# Let's see what is inside both
pos1_end = html.find('};', pos1)
print("=== Head switchTab ===")
print(html[pos1:pos1_end+2])

if pos2 != -1:
    pos2_end = html.find('};', pos2)
    print("\n=== Body switchTab ===")
    print(html[pos2:pos2_end+2])
