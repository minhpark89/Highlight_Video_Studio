from pathlib import Path

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect pane-posts top buttons
pos_posts = html.find('id="pane-posts"')
pos_end_btn = html.find('<div style="overflow-x: auto;', pos_posts)
print("=== PANE-POSTS TOP BUTTONS ===")
print(html[pos_posts:pos_end_btn])
