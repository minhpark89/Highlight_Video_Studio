from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
pos = html.find('async function loadPostsTable')
pos_end = html.find('tbody.innerHTML = rows;', pos)
with open(r"D:\Highlight_Video_Studio\curr_load_posts.txt", "w", encoding="utf-8") as f:
    f.write(html[pos:pos_end+50])
print("Saved curr_load_posts.txt, length:", pos_end - pos)
