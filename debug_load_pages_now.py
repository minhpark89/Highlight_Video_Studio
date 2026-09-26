from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect loadTokensAndPages in index.html
pos = html.find('async function loadTokensAndPages()')
pos_end = html.find('function updateScheduleGroupSummary', pos)
print("=== loadTokensAndPages ===")
print(html[pos:pos+2500])
