from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect gallery rendering in index.html
pos = html.find('renderGallery')
if pos == -1: pos = html.find('loadGallery')
if pos == -1: pos = html.find('loadClips')

print("Gallery JS pos:", pos)
if pos != -1:
    print(html[pos:pos+2000])

# Look for badge-posted or is_posted
for line in html.splitlines():
    if 'is_posted' in line or 'ĐÃ POST' in line or 'badge-posted' in line:
        print(line)
