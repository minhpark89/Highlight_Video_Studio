from pathlib import Path

content = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
pos = content.find("async function loadPostsTable")
pos_end = content.find("tbody.innerHTML = html;", pos)
if pos_end == -1: pos_end = content.find("tbody.innerHTML = rows;", pos)
print("=== CURRENT loadPostsTable in templates/index.html ===")
print(content[pos:pos_end+50])
