from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's search where "343 video" or gallery count is rendered
pos = html.find('id="gallery-count"')
if pos == -1: pos = html.find('Thư viện Highlight Clips')
print(html[pos-100:pos+600])

# Search for renderGallery or loadGallery
pos_fn = html.find('function renderGallery')
if pos_fn == -1: pos_fn = html.find('function loadGallery')
if pos_fn == -1: pos_fn = html.find('async function loadClips')
print("\n=== Gallery JS Function ===")
print(html[pos_fn:pos_fn+1500])
