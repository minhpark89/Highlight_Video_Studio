from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect loadPostsTable in index.html
pos = html.find('function loadPostsTable(')
if pos == -1: pos = html.find('async function loadPostsTable(')
print(html[pos:pos+1500])
