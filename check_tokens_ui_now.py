from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect pane-tokens in templates/index.html
pos = html.find('id="pane-tokens"')
pos_table = html.find('<table', pos)
print("=== PANE-TOKENS HEADER ===")
print(html[pos:pos_table])
