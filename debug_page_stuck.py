from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect loadTokensAndPages in index.html
pos = html.find('async function loadTokensAndPages()')
print("loadTokensAndPages pos:", pos)

pos_render = html.find('renderFilteredPages', pos)
print("renderFilteredPages pos after loadTokensAndPages:", pos_render)

# Let's print 2000 chars from loadTokensAndPages
print(html[pos:pos+2500])
