from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where statusBadge is rendered in loadPostsTable
pos = html.find('async function loadPostsTable()')
pos_end = html.find('tbody.innerHTML = html;', pos)
if pos_end == -1: pos_end = html.find('tbody.innerHTML = rows;', pos)
print("=== loadPostsTable snippet ===")
print(html[pos:pos_end+50])
