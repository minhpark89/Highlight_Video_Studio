from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's see the two switchTab definitions in index.html
pos1 = html.find('window.switchTab = function')
pos2 = html.find('window.switchTab = function', pos1 + 30)
print(f"Pos1: {pos1}, Pos2: {pos2}")

# Let's inspect Pos2
if pos2 != -1:
    pos2_end = html.find('};', pos2)
    print("=== POS2 (BODY SCRIPT) ===")
    print(html[pos2:pos2_end+2])
