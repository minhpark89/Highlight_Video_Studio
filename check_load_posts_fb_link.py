from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect loadPostsTable in templates/index.html
pos = html.find('async function loadPostsTable')
if pos == -1: pos = html.find('function loadPostsTable')
pos_end = html.find('tbody.innerHTML = rows;', pos)
print("=== loadPostsTable snippet ===")
print(html[pos:pos_end+50])
