from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect pane-pages
pos_p = html.find('id="pane-pages"')
pos_end = html.find('id="fb-page-cards-grid"', pos_p)
with open(r"D:\Highlight_Video_Studio\pane_pages_header.txt", "w", encoding="utf-8") as f:
    f.write(html[pos_p:pos_end])

# Let's inspect pane-posts
pos_posts = html.find('id="pane-posts"')
pos_posts_end = html.find('<table', pos_posts)
with open(r"D:\Highlight_Video_Studio\pane_posts_header.txt", "w", encoding="utf-8") as f:
    f.write(html[pos_posts:pos_posts_end])

print("Wrote text files!")
