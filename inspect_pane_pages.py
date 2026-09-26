from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect pane-pages
pos_pages = html.find('id="pane-pages"')
pos_pages_end = html.find('id="fb-page-cards-grid"', pos_pages)
print("=== PANE PAGES HEADER/TOOLBAR ===")
print(html[pos_pages:pos_pages_end])
