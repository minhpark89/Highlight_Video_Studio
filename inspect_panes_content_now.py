from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's inspect pane-tokens content
pos = html.find('id="pane-tokens"')
pos_end = html.find('</section>', pos)
print("=== PANE-TOKENS ===")
print(html[pos:pos+2000])

pos_g = html.find('id="pane-groups"')
pos_g_end = html.find('</section>', pos_g)
print("\n=== PANE-GROUPS ===")
print(html[pos_g:pos_g+2000])
