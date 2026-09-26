from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect around line 180119 where loadTokensAndPages is defined
pos = html.find('async function loadTokensAndPages()')
print("loadTokensAndPages pos:", pos)
print(html[pos:pos+1500])
