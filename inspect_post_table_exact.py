from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where statusBadge is rendered in loadPostsTable
pos = html.find("let statusBadge = '';")
pos_end = html.find("tbody.innerHTML", pos)
print("=== CURRENT statusBadge & table row generation ===")
print(html[pos:pos_end+50])
