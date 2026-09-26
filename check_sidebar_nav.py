from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect sidebar navigation buttons
pos = html.find('class="sidebar"')
if pos == -1: pos = html.find('<aside')
if pos == -1: pos = html.find('nav-btn')

print(html[pos-100:pos+1500])
