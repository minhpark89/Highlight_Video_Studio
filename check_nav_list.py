from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

pos_nav = html.find('class="nav-list"')
if pos_nav == -1: pos_nav = html.find('<nav')
print(html[pos_nav:pos_nav+1500])
