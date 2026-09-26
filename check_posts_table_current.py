from pathlib import Path
import re

html_tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
text = html_tmpl.read_text(encoding="utf-8")

# Let's inspect where statusBadge is created in loadPostsTable:
pos = text.find("async function loadPostsTable")
pos_end = text.find("tbody.innerHTML = html;", pos)
if pos_end == -1: pos_end = text.find("tbody.innerHTML = rows;", pos)

print("=== loadPostsTable in templates/index.html ===")
print(text[pos:pos_end+30])
