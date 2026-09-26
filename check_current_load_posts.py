from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = tmpl.read_text(encoding="utf-8")

pos = html.find('async function loadPostsTable')
pos_end = html.find('tbody.innerHTML = rows;', pos)
print("=== loadPostsTable in templates/index.html ===")
print(html[pos:pos_end+50])
