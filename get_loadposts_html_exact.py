from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where posts are rendered into rows
pos = html.find('async function loadPostsTable()')
pos_end = html.find('tbody.innerHTML = html;', pos)
if pos_end == -1: pos_end = html.find('tbody.innerHTML = rows;', pos)
print("loadPostsTable in templates/index.html:\n", html[pos:pos_end+50])
