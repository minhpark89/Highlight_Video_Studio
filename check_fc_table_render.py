from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where First Comment is formatted in index.html (client side rendering)
pos = html.find('loadPostsTable')
pos_end = html.find('tbody.innerHTML', pos)
print(html[pos:pos+2500])
