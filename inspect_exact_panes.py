from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect pane-pages
pos_p = html.find('id="pane-pages"')
pos_p_end = html.find('id="fb-page-cards-grid"', pos_p)
print("=== PANE-PAGES HEADER ===")
print(html[pos_p:pos_p_end])

# Let's inspect pane-posts toolbar
pos_posts = html.find('id="pane-posts"')
pos_posts_table = html.find('<table', pos_posts)
print("\n=== PANE-POSTS TOOLBAR ===")
print(html[pos_posts:pos_posts_table])
