from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect pane-pages where filters/toolbar are located
pos_pages = html.find('id="pane-pages"')
pos_grid = html.find('id="fb-page-cards-grid"', pos_pages)

with open(r"D:\Highlight_Video_Studio\pages_toolbar.html", "w", encoding="utf-8") as f:
    f.write(html[pos_pages:pos_grid])

print("Wrote pages_toolbar.html successfully!")
