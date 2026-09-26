from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
print("Total chars in index.html:", len(html))

# Let's inspect pane-posts and search for loadPostsTable
pos_fn = html.find("loadPostsTable")
while pos_fn != -1:
    print("Found loadPostsTable at:", pos_fn)
    print(html[pos_fn:pos_fn+300])
    print("-" * 50)
    pos_fn = html.find("loadPostsTable", pos_fn + 1)
