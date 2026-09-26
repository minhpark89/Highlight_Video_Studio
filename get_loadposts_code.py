from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

pos = html.find('async function loadPostsTable()')
pos_end = html.find('tbody.innerHTML = html;', pos)
if pos_end == -1: pos_end = html.find('tbody.innerHTML = rows;', pos)
if pos_end == -1: pos_end = pos + 3000

print("=== loadPostsTable CODE ===")
print(html[pos:pos_end+50])
