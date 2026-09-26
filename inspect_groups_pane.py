from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's inspect pane-groups HTML
pos = html.find('id="pane-groups"')
pos_end = html.find('</section>', pos)
print("=== PANE-GROUPS HTML ===")
print(html[pos:pos_end+10])
