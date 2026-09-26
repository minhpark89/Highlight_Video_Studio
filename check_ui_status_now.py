from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = tmpl.read_text(encoding="utf-8")

# Let's inspect pane-tokens in templates/index.html:
pos_tokens = html.find('id="pane-tokens"')
pos_table = html.find('<table', pos_tokens)
print("=== PANE-TOKENS CONTROLS IN TEMPLATES ===")
print(html[pos_tokens:pos_table])

# Let's inspect where statusBadge is defined in templates/index.html:
pos_sb = html.find("let statusBadge = '';")
print("\n=== statusBadge in templates/index.html ===")
print(html[pos_sb:pos_sb+600])
