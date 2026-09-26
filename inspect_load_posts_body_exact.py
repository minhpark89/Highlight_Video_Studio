from pathlib import Path
import re

html_tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
text = html_tmpl.read_text(encoding="utf-8")

# Let's inspect where posts are rendered in loadPostsTable
pos = text.find('async function loadPostsTable()')
pos_end = text.find('tbody.innerHTML = rows;', pos)
print("=== loadPostsTable snippet ===")
print(text[pos:pos_end+50])
