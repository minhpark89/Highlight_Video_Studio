from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect loadTokensAndPages in index.html
pos = html.find('async function loadTokensAndPages(')
if pos == -1: pos = html.find('function loadTokensAndPages(')
pos_end = html.find('function renderFbPageCards', pos)
print("=== loadTokensAndPages ===")
print(html[pos:pos_end])

pos_render = html.find('function renderFbPageCards()')
pos_render_end = html.find('function renderPagination', pos_render)
print("\n=== renderFbPageCards ===")
print(html[pos_render:pos_render+1200])
