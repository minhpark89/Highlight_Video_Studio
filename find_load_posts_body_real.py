from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
lines = html.splitlines()

# Let's inspect line 239846 from our earlier search
for i in range(239840 // 50, min(len(lines), 239840 // 50 + 80)): # wait, line number vs char index
    pass

# Search for "async function loadPostsTable()"
pos = html.find("async function loadPostsTable()")
print("pos of loadPostsTable:", pos)
if pos != -1:
    pos_end = html.find("tbody.innerHTML = rows;", pos)
    print(html[pos:pos_end+30])
