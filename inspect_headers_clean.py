from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect pane-pages
pos_p = html.find('id="pane-pages"')
pos_end = html.find('id="fb-page-cards-grid"', pos_p)
print("=== PANE-PAGES HEADER ===")
print(html[pos_p:pos_end])

# Let's inspect pane-groups
pos_g = html.find('id="pane-groups"')
pos_g_end = html.find('<table', pos_g)
print("\n=== PANE-GROUPS HEADER ===")
print(html[pos_g:pos_g_end])
