from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = tmpl.read_text(encoding="utf-8")

# Let's inspect pane-posts top toolbar
pos_posts = html.find('id="pane-posts"')
pos_table = html.find('<table', pos_posts)

# Look for buttons in pane-posts header
print(html[pos_posts:pos_table])
