from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = tmpl.read_text(encoding="utf-8")

# Let's inspect renderGallery / loadGallery / filterClips in index.html
pos = html.find('function renderGallery')
if pos == -1: pos = html.find('function loadGallery')
if pos == -1: pos = html.find('loadClips')

print("Gallery JS pos:", pos)
if pos != -1:
    print(html[pos:pos+1500])
