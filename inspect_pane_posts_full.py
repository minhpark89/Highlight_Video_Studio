from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

pos_posts = html.find('id="pane-posts"')
print(html[pos_posts:pos_posts+1600])
