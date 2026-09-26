from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
pos = html.find('async function loadPostsTable')
pos_end = html.find('tbody.innerHTML = rows;', pos)
with open(r"D:\Highlight_Video_Studio\load_posts_body.txt", "w", encoding="utf-8") as f:
    f.write(html[pos:pos_end+50])
print("Dumped loadPostsTable body, length:", pos_end - pos)
