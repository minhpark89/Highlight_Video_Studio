from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect line 1590 to 1650 in index.html around renderFilteredPages
pos = html.find('function renderFilteredPages()')
print("renderFilteredPages pos:", pos)
if pos != -1:
    print(html[pos:pos+2500])
