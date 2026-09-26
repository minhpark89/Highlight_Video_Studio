from pathlib import Path

html_tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
html_web = Path(r"D:\Highlight_Video_Studio\web\index.html").read_text(encoding="utf-8")

pos_tmpl = html_tmpl.find('async function loadPostsTable')
pos_end_tmpl = html_tmpl.find('tbody.innerHTML = rows;', pos_tmpl)
print("=== TEMPLATES loadPostsTable ===")
print(html_tmpl[pos_tmpl:pos_end_tmpl+30])

pos_web = html_web.find('async function loadPostsTable')
pos_end_web = html_web.find('tbody.innerHTML = rows;', pos_web)
print("\n=== WEB/INDEX loadPostsTable ===")
print(html_web[pos_web:pos_end_web+30])
