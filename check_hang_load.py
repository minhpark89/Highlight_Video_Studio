from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect loadTokensAndPages definition
pos = html.find('async function loadTokensAndPages')
if pos == -1: pos = html.find('function loadTokensAndPages')

pos_end = html.find('function renderFilteredPages', pos)
print("loadTokensAndPages pos:", pos, "renderFilteredPages pos:", pos_end)
print(html[pos:pos+1500])
