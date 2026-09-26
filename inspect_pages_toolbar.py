from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = tmpl.read_text(encoding="utf-8")

# Let's inspect pane-pages toolbar & search bar
pos_pages = html.find('id="pane-pages"')
pos_table = html.find('id="fb-page-cards-grid"', pos_pages)
print("=== PANE-PAGES TOOLBAR CURRENT ===")
print(html[pos_pages:pos_table])
