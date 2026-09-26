from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

pos = html.find('async function loadTokensAndPages')
pos_end = html.find('function renderPagination', pos)
print("=== loadTokensAndPages to renderPagination ===")
print(html[pos:pos_end+500])
