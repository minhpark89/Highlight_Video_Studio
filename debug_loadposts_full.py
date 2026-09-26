from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect loadPostsTable in index.html
pos = html.find('async function loadPostsTable()')
print("pos of loadPostsTable:", pos)
if pos != -1:
    pos_end = html.find('tbody.innerHTML', pos)
    print(html[pos:pos+3500])
