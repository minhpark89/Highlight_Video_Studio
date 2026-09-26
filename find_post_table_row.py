import re
from pathlib import Path

html_tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
text = html_tmpl.read_text(encoding="utf-8")

# Let's inspect where posts are rendered into table rows in templates/index.html
# Search for posts-table-body
pos = text.find('posts-table-body')
pos_fn = text.find('async function loadPostsTable', pos - 5000)
if pos_fn == -1: pos_fn = text.find('function loadPostsTable', pos - 5000)

print("loadPostsTable pos:", pos_fn)
# Look for rows += `...
pos_rows = text.find('rows +=', pos_fn)
pos_rows_end = text.find('tbody.innerHTML', pos_rows)
print("=== ROW TEMPLATE ===")
print(text[pos_rows:pos_rows_end])
