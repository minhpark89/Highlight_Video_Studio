from pathlib import Path
import re

html_tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
text = html_tmpl.read_text(encoding="utf-8")

# Let's inspect line 2000 to 2200 where posts table is rendered
# Search for posts-table-body
pos = text.find('id="posts-table-body"')
print("posts-table-body at:", pos)

# Find where posts-table-body is populated
matches = [m.start() for m in re.finditer(r'posts-table-body', text)]
print("Occurrences of posts-table-body:", matches)
for m in matches:
    print(text[m-50:m+500])
    print("="*40)
