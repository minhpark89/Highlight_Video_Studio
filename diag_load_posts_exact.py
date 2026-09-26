from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where posts are rendered into rows
pos = html.find('posts-table-body')
print("posts-table-body at:", pos)

# Find where innerHTML of posts-table-body is set
pos_js = html.find("loadPostsTable")
while pos_js != -1:
    print(f"=== pos {pos_js} ===")
    print(html[pos_js:pos_js+600])
    pos_js = html.find("loadPostsTable", pos_js+1)
