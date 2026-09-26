from pathlib import Path
import re

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where posts are rendered into table rows in templates/index.html
# Search for posts-table-body
pos = html.find('posts-table-body')
pos_fn = html.find('async function loadPostsTable', pos - 5000)
if pos_fn == -1: pos_fn = html.find('function loadPostsTable', pos - 5000)

print("loadPostsTable pos:", pos_fn)
# Look for rows += `...
pos_rows = html.find('rows +=', pos_fn)
pos_rows_end = html.find('tbody.innerHTML', pos_rows)
print("=== ROW TEMPLATE ===")
print(html[pos_rows:pos_rows_end])
