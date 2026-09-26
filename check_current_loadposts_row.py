from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where loadPostsTable is defined in index.html
pos = html.find('async function loadPostsTable()')
if pos == -1: pos = html.find('function loadPostsTable()')
print("loadPostsTable pos:", pos)

# Find where rows are appended
pos_rows = html.find('rows +=', pos)
pos_rows_end = html.find('tbody.innerHTML', pos_rows)
print("=== CURRENT loadPostsTable ROW TEMPLATE ===")
print(html[pos_rows:pos_rows_end])
