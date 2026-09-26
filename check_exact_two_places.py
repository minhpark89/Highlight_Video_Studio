from pathlib import Path

content = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# 1. Check pane-tokens
pos_tok = content.find('id="pane-tokens"')
pos_table = content.find('<table', pos_tok)
print("=== PANE TOKENS SLICE ===")
print(content[pos_tok:pos_table])

# 2. Check loadPostsTable
pos_lp = content.find('async function loadPostsTable()')
pos_end_lp = content.find('tbody.innerHTML', pos_lp)
print("\n=== loadPostsTable SLICE ===")
print(content[pos_lp:pos_end_lp+30])
