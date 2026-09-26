from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
print("Is 'Xem Reel Facebook' in templates/index.html?", "Xem Reel Facebook" in html)

# Let's inspect loadPostsTable in index.html
pos = html.find('async function loadPostsTable')
if pos == -1: pos = html.find('function loadPostsTable')
pos_end = html.find('tbody.innerHTML = rows;', pos)
print("loadPostsTable in templates/index.html:\n", html[pos:pos_end+30])
