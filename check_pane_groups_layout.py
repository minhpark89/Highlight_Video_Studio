from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

pos = html.find('id="pane-groups"')
print("Position of pane-groups:", pos)
# Let's inspect 1000 characters before and after pos
print("=== BEFORE pane-groups ===")
print(html[pos-800:pos])
print("=== AT pane-groups ===")
print(html[pos:pos+800])
