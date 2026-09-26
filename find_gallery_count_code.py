from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's search where "video" count or "Đã đăng" count is calculated in index.html
pos = html.find('343 video')
if pos == -1: pos = html.find('loadGallery')
if pos == -1: pos = html.find('renderGallery')

print("Gallery search pos:", pos)
if pos != -1:
    print(html[pos-100:pos+1200])

# Also search for 'badge-posted' or 'ĐÃ POST' in index.html
for line in html.splitlines():
    if 'ĐÃ POST' in line or 'badge-posted' in line or 'filterClips' in line:
        print(line)
