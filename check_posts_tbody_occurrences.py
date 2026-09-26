from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where posts are rendered
pos = html.find('posts-table-body')
while pos != -1:
    print(f"Occurrence at {pos}:")
    print(html[pos-50:pos+350])
    pos = html.find('posts-table-body', pos+1)
