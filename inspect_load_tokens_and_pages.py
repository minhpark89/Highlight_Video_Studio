from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = tmpl.read_text(encoding="utf-8")

# Let's inspect renderFbPageCards and loadTokensAndPages in index.html
pos = html.find('async function loadTokensAndPages()')
print("loadTokensAndPages pos:", pos)
if pos != -1:
    print(html[pos:pos+1500])
