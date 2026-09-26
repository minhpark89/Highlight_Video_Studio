from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect renderFbPageCards to see how filtering by group works
pos = html.find('function renderFbPageCards(')
print(html[pos:pos+1500])
