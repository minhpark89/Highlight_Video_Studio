from pathlib import Path

html_tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
pos = html_tmpl.find('async function loadPostsTable')
pos_end = html_tmpl.find('tbody.innerHTML = rows;', pos)
print("=== loadPostsTable in templates/index.html ===")
print(html_tmpl[pos:pos_end+30])
