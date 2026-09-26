from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = tmpl.read_text(encoding="utf-8")

# Let's inspect pane-pages to see where to insert loha-page-group-pills
pos_pages = html.find('id="pane-pages"')
# Find where the search filter row or cards grid starts
pos_grid = html.find('id="fb-page-cards-grid"', pos_pages)

# Look for toolbar inside pane-pages
snippet = html[pos_pages:pos_grid]
# Let's place the pills bar right before id="fb-page-cards-grid" or right below the search bar
print("Snippet before cards grid:\n", snippet[-600:])
