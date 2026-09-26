from pathlib import Path

content = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where posts-table-body is and where loadPostsTable is
pos = content.find("async function loadPostsTable()")
print("loadPostsTable in templates/index.html at:", pos)
if pos != -1:
    pos_end = content.find("tbody.innerHTML", pos)
    print(content[pos:pos_end+50])
