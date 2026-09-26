from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect pane-pages in index.html
pos_pages = html.find('id="pane-pages"')
pos_pages_end = html.find('</section>', pos_pages)
print("pane-pages slice:", pos_pages, pos_pages_end)
print(html[pos_pages:pos_pages+1200])
