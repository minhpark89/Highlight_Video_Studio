from pathlib import Path

tmpl_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = tmpl_path.read_text(encoding="utf-8")

# 1. Look for pane-tokens controls in html
pos_tok = html.find('id="pane-tokens"')
pos_table = html.find('<table', pos_tok)
old_pane_tokens_header = html[pos_tok:pos_table]

print("=== CURRENT PANE TOKENS HEADER ===")
print(old_pane_tokens_header)
