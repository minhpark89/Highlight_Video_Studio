from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect loadTokensAndPages around line 180100
pos = html.find("async function loadTokensAndPages()")
pos_end = html.find("function renderFilteredPages", pos)
print("=== loadTokensAndPages ===")
print(html[pos:pos_end])

pos_render = html.find("function renderFilteredPages()")
pos_render_end = html.find("function renderPagination", pos_render)
print("\n=== renderFilteredPages ===")
print(html[pos_render:pos_render+1500])
