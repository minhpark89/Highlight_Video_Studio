from pathlib import Path

content = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect line 239846 where loadPostsTable is
pos = content.find("async function loadPostsTable()")
print("pos of loadPostsTable:", pos)
if pos != -1:
    pos_end = content.find("tbody.innerHTML", pos)
    print(content[pos:pos_end+50])
