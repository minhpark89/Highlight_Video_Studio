from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
print("has 'Xem Reel Facebook' in templates/index.html?", "Xem Reel Facebook" in html)

web_idx = Path(r"D:\Highlight_Video_Studio\web\index.html").read_text(encoding="utf-8")
print("has 'Xem Reel Facebook' in web/index.html?", "Xem Reel Facebook" in web_idx)

# Let's inspect loadPostsTable in templates/index.html
pos = html.find('async function loadPostsTable')
pos_end = html.find('tbody.innerHTML = rows;', pos)
print("=== loadPostsTable row snippet ===")
print(html[pos:pos_end+50])
