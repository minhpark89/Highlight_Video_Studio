from pathlib import Path
import re

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect pane-posts to see current action buttons
pos_posts = html.find('id="pane-posts"')
pos_table = html.find('<table', pos_posts)
print("=== PANE-POSTS HEADER ===")
print(html[pos_posts:pos_table])
