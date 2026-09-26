from pathlib import Path
import re

tmpl_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = tmpl_path.read_text(encoding="utf-8")

# 1. ADD REEL LINK TO loadPostsTable
# Find loadPostsTable in html
pos_lpt = html.find('async function loadPostsTable()')
if pos_lpt != -1:
    pos_sub = html.find("p.status === 'published'", pos_lpt)
    if pos_sub != -1:
        # Check snippet
        print("Found published check in loadPostsTable at:", pos_sub)
        old_part = html[pos_sub-20:pos_sub+200]
        print("Old snippet:\n", old_part)

# 2. Check pane-tokens controls
pos_tok = html.find('id="pane-tokens"')
pos_table = html.find('<table', pos_tok)
print("\nPane tokens controls:\n", html[pos_tok:pos_table])
