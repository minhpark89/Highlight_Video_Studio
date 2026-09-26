from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect loadTokensAndPages to ensure loadPageGroupsPills is called
pos_ltp = html.find('async function loadTokensAndPages()')
print("loadTokensAndPages snippet:\n", html[pos_ltp:pos_ltp+400])
