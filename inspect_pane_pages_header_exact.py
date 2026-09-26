from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect pane-pages where the filter controls currently are
pos_p = html.find('id="pane-pages"')
pos_end = html.find('id="fb-page-cards-grid"', pos_p)
print("=== PANE-PAGES HEADER & FILTER ===")
print(html[pos_p:pos_end])
