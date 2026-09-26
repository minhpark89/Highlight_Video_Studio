from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect loadTokensAndPages around line 180119
pos = html.find("async function loadTokensAndPages()")
print("loadTokensAndPages pos:", pos)
print(html[pos:pos+2000])
