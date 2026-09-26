from pathlib import Path

html_tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where loadPostsTable is in index.html
pos = html_tmpl.find("async function loadPostsTable()")
if pos == -1: pos = html_tmpl.find("function loadPostsTable()")

print("loadPostsTable pos:", pos)
print(html_tmpl[pos:pos+2500])
