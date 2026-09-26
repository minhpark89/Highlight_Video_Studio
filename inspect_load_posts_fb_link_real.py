from pathlib import Path
import re

html_tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
html_web = Path(r"D:\Highlight_Video_Studio\web\index.html").read_text(encoding="utf-8")

# Let's inspect where loadPostsTable renders table rows
# Look for posts-table-body
pos = html_tmpl.find("async function loadPostsTable")
pos_end = html_tmpl.find("tbody.innerHTML = rows;", pos)
print("=== TEMPLATES loadPostsTable ===")
print(html_tmpl[pos:pos_end+30])
