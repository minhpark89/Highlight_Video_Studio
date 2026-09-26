from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where "Đang nạp danh sách Fanpage Facebook" is in index.html
pos = html.find('Đang nạp danh sách Fanpage Facebook')
print("Position:", pos)
if pos != -1:
    print(html[pos-100:pos+300])

# Find which JS function populates this
pos_fn = html.find('async function loadTokensAndPages')
if pos_fn == -1: pos_fn = html.find('function loadTokensAndPages')
print("loadTokensAndPages pos:", pos_fn)
if pos_fn != -1:
    print(html[pos_fn:pos_fn+1500])
