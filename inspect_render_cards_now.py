from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = tmpl.read_text(encoding="utf-8")

# Let's inspect renderFbPageCards in index.html
pos = html.find('function renderFbPageCards()')
if pos != -1:
    pos_end = html.find('function renderPagination(', pos)
    if pos_end == -1: pos_end = pos + 2500
    print("=== renderFbPageCards ===")
    print(html[pos:pos_end])
