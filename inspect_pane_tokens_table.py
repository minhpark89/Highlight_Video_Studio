from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's inspect pane-tokens and see how tokens are rendered
pos = html.find('id="pane-tokens"')
pos_end = html.find('</section>', pos)
print("pane-tokens length:", pos_end - pos)
print(html[pos:pos+1500])
