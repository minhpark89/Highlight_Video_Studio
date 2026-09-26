import re
from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = tmpl.read_text(encoding="utf-8")

# Let's find pane-pages
pos_pages = html.find('id="pane-pages"')
pos_pages_end = html.find('</section>', pos_pages)
print("pane-pages slice length:", pos_pages_end - pos_pages)
print("pane-pages preview:\n", html[pos_pages:pos_pages+600])

# Let's find pane-posts
pos_posts = html.find('id="pane-posts"')
pos_posts_end = html.find('</section>', pos_posts)
print("pane-posts slice length:", pos_posts_end - pos_posts)
print("pane-posts preview:\n", html[pos_posts:pos_posts+600])
