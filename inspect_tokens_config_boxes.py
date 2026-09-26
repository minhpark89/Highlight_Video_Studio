from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect pane-tokens in index.html to see where the configuration boxes are
pos = html.find('id="pane-tokens"')
pos_end = html.find('id="tokens-table-body"', pos)
print("=== PANE-TOKENS HEADER / CONFIG BOXES ===")
print(html[pos:pos_end])
