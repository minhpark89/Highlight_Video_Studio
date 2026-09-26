from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where statusBadge is rendered in loadPostsTable
pos = html.find("let statusBadge = '';")
print("statusBadge pos:", pos)
if pos != -1:
    print(html[pos:pos+1500])
