from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect pane-tokens top controls
pos_tokens = html.find('id="pane-tokens"')
pos_table = html.find('<table', pos_tokens)
print("=== PANE-TOKENS TOP CONTROLS ===")
print(html[pos_tokens:pos_table])
