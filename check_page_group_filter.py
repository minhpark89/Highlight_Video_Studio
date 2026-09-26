from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where fb-page-filter-group or group filter is in pane-pages
pos = html.find('id="fb-page-filter-group"')
print("fb-page-filter-group pos:", pos)
if pos != -1:
    print(html[pos-200:pos+400])

# Let's inspect renderFbPageCards or loadTokensAndPages
pos_fn = html.find('function renderFbPageCards(')
if pos_fn == -1: pos_fn = html.find('function loadTokensAndPages(')
print("\nJS Function preview:")
print(html[pos_fn:pos_fn+800])
