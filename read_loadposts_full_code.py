from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
pos = html.find('async function loadPostsTable()')
pos_end = html.find('tbody.innerHTML', pos)
print("=== loadPostsTable from templates/index.html ===")
print(html[pos:pos_end+30])
