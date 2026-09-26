from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where posts are rendered
pos = html.find('posts-table-body')
print("posts-table-body pos:", pos)

# Let's inspect where getElementById('posts-table-body') is used in index.html
pos_tb = html.find("getElementById('posts-table-body')")
while pos_tb != -1:
    print(f"=== pos {pos_tb} ===")
    print(html[pos_tb-50:pos_tb+600])
    pos_tb = html.find("getElementById('posts-table-body')", pos_tb + 1)
