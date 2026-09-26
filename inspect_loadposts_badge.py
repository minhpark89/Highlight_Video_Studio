from pathlib import Path

content = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where statusBadge is defined in loadPostsTable
pos = content.find("let statusBadge = '';")
if pos == -1: pos = content.find("statusBadge")
print("statusBadge pos:", pos)
print(content[pos-50:pos+800])
