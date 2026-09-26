from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where posts are rendered into rows
pos = html.find("posts-table-body")
print("posts-table-body at:", pos)

# Find function that sets innerHTML of posts-table-body
pos_tbody = html.find("document.getElementById('posts-table-body')")
while pos_tbody != -1:
    print(f"=== pos {pos_tbody} ===")
    print(html[pos_tbody:pos_tbody+500])
    pos_tbody = html.find("document.getElementById('posts-table-body')", pos_tbody + 1)
