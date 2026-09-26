from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where switchTab handles pane-pages
pos = html.find("switchTab")
print(html[pos:pos+1500])
