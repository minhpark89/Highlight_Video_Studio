from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect loadPostsTable in index.html
pos = html.find('async function loadPostsTable')
pos_end = html.find('tbody.innerHTML = rows;', pos)
if pos_end == -1: pos_end = pos + 3000
print("=== loadPostsTable in index.html ===")
print(html[pos:pos_end+50])
