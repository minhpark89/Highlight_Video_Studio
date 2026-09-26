from pathlib import Path
import re

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect how posts-table renders rows in index.html
pos = html.find('async function loadPostsTable')
if pos == -1: pos = html.find('function loadPostsTable')
print("=== loadPostsTable in index.html ===")
print(html[pos:pos+2000])
