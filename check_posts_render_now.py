from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where posts are rendered into rows
pos = html.find('const tbody = document.getElementById(\'posts-table-body\');')
print("Found posts-table-body at pos:", pos)
if pos != -1:
    print(html[pos:pos+2500])
