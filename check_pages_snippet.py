from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's see how groups are handled in pane-pages
pos_pages = html.find('id="pane-pages"')
pos_cards = html.find('id="fb-page-cards-grid"', pos_pages)
snippet = html[pos_pages:pos_cards]
print("=== PANE-PAGES TOOLBAR SNIPPET ===")
print(snippet)
