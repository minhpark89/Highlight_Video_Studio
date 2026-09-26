from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect loadTokensAndPages in index.html
pos = html.find('async function loadTokensAndPages')
if pos == -1: pos = html.find('function loadTokensAndPages')
print("loadTokensAndPages pos:", pos)
print(html[pos:pos+1500])
