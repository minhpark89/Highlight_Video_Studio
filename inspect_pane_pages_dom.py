from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect pane-pages in index.html to see what table or grid is used
pos_pages = html.find('id="pane-pages"')
pos_pages_end = html.find('</section>', pos_pages)
print("=== PANE-PAGES ===")
print(html[pos_pages:pos_pages+3000])
