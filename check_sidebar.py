from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's see what is in sidebar navigation
pos_nav = html.find('<nav')
if pos_nav == -1: pos_nav = html.find('class="sidebar"')
print("=== SIDEBAR NAV ===")
print(html[pos_nav:pos_nav+1000])
