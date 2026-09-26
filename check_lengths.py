from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect pane-pages
pos_p = html.find('id="pane-pages"')
pos_p_end = html.find('</section>', pos_p)
print("pane-pages length:", pos_p_end - pos_p)

# Let's inspect pane-groups
pos_g = html.find('id="pane-groups"')
pos_g_end = html.find('</section>', pos_g)
print("pane-groups length:", pos_g_end - pos_g)

# Let's inspect pane-posts
pos_post = html.find('id="pane-posts"')
pos_post_end = html.find('</section>', pos_post)
print("pane-posts length:", pos_post_end - pos_post)
