from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = tmpl.read_text(encoding="utf-8")

# Let's inspect pane-pages where filters/toolbar are located
pos_pages = html.find('id="pane-pages"')
pos_grid = html.find('id="fb-page-cards-grid"', pos_pages)
print("=== PANE-PAGES TOOLBAR SLICE ===")
print(html[pos_pages:pos_grid])
