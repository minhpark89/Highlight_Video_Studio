from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect pane-tokens controls
pos = html.find('id="pane-tokens"')
pos_table = html.find('<table', pos)
print("=== PANE-TOKENS CONTROLS ===")
print(html[pos:pos_table])
