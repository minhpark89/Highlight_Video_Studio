from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's inspect the switchTab in body (around pos 79061)
pos = html.find('window.switchTab = function')
pos2 = html.find('window.switchTab = function', pos + 30)
print("pos1:", pos, "pos2:", pos2)
if pos2 != -1:
    print("=== POS2 (BODY) ===")
    print(html[pos2:pos2+1000])
