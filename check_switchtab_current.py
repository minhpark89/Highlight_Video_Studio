from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's inspect switchTab in body script:
pos = html.find('[Tab] Switching to:')
if pos != -1:
    pos_start = html.rfind('window.switchTab = function', 0, pos)
    pos_end = html.find('};\n', pos)
    if pos_end == -1: pos_end = html.find('};', pos)
    print("=== Found switchTab in body ===")
    print(html[pos_start:pos_end+2])
