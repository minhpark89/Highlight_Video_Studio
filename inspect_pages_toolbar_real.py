from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = tmpl.read_text(encoding="utf-8")

# Let's inspect pane-pages toolbar and where groups are filtered
pos = html.find('id="pane-pages"')
pos_end = html.find('id="fb-page-cards-grid"', pos)
print("=== PANE-PAGES TOOLBAR CURRENT ===")
print(html[pos:pos_end])
