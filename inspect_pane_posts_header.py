from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = tmpl.read_text(encoding="utf-8")

# Let's inspect pane-posts header to see where to place the "Hủy bài đang hẹn" button
pos_posts = html.find('id="pane-posts"')
pos_table = html.find('<table', pos_posts)
print(html[pos_posts:pos_table])
