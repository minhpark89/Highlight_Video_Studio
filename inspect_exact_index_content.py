from pathlib import Path

tmpl_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = tmpl_path.read_text(encoding="utf-8")

# 1. Look for pane-tokens controls
pos_tokens = html.find('id="pane-tokens"')
pos_table = html.find('<table', pos_tokens)
print("=== PANE-TOKENS SLICE ===")
print(html[pos_tokens:pos_table])

# 2. Look for loadPostsTable in html
pos_lp = html.find('async function loadPostsTable')
if pos_lp == -1: pos_lp = html.find('function loadPostsTable')
print("\n=== loadPostsTable SLICE ===")
print(html[pos_lp:pos_lp+1200])
