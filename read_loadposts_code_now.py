from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

pos = html.find('async function loadPostsTable()')
pos_end = html.find('tbody.innerHTML = html;', pos)
print("=== loadPostsTable CODE ===")
print(html[pos:pos_end+30])
