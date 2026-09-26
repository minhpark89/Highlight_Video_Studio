from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect loadTokensAndPages and renderFbPageCards in templates/index.html
pos = html.find('async function loadTokensAndPages()')
print("=== loadTokensAndPages ===")
print(html[pos:pos+2500])
