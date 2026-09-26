from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

def get_pane(name):
    pos = html.find(f'id="{name}"')
    if pos == -1: return "None"
    end = html.find('</section>', pos)
    return html[pos:end]

pane_pages = get_pane("pane-pages")
pane_groups = get_pane("pane-groups")
pane_posts = get_pane("pane-posts")

print("pane-pages length:", len(pane_pages))
print("pane-groups length:", len(pane_groups))
print("pane-posts length:", len(pane_posts))

# Let's write them to F: workspace so they can be read easily
Path(r"F:\openclaw\.openclaw\workspace\debug_pane_pages.html").write_text(pane_pages, encoding="utf-8")
Path(r"F:\openclaw\.openclaw\workspace\debug_pane_groups.html").write_text(pane_groups, encoding="utf-8")
Path(r"F:\openclaw\.openclaw\workspace\debug_pane_posts.html").write_text(pane_posts, encoding="utf-8")
print("Saved to workspace debug files successfully!")
