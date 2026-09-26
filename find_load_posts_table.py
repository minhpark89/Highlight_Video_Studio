from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect pane-posts table body
pos = html.find('id="posts-table-body"')
print("posts-table-body pos:", pos)

# Find where posts-table-body is updated
pos_js = html.find("loadPostsTable")
while pos_js != -1:
    print(f"=== pos {pos_js} ===")
    print(html[pos_js:pos_js+500])
    pos_js = html.find("loadPostsTable", pos_js+1)
