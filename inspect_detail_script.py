from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect pane-pages
pos_pages = html.find('id="pane-pages"')
pos_pages_end = html.find('</section>', pos_pages)
print("=== PANE-PAGES ===")
print(html[pos_pages:pos_pages+2500])

# Let's inspect pane-posts
pos_posts = html.find('id="pane-posts"')
pos_posts_end = html.find('</section>', pos_posts)
print("\n=== PANE-POSTS ===")
print(html[pos_posts:pos_posts+1800])
