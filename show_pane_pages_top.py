from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

pos_pages = html.find('id="pane-pages"')
pos_cards = html.find('id="fb-page-cards-grid"', pos_pages)
print(html[pos_pages:pos_cards])
