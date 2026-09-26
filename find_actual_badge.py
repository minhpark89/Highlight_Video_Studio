from pathlib import Path

content = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect line 239846
pos = content.find("function loadPostsTable()")
if pos == -1: pos = content.find("loadPostsTable()")
print("loadPostsTable pos:", pos)

pos_badge = content.find("let statusBadge = '';", pos)
print("statusBadge pos:", pos_badge)
print(content[pos_badge:pos_badge+800])
