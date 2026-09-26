from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where 'Đang nạp danh sách Fanpage Facebook' is
pos = html.find('Đang nạp danh sách Fanpage Facebook')
print("Position:", pos)
if pos != -1:
    print(html[pos-100:pos+300])

# Where is this container filled?
# Check loadTokensAndPages or renderFbPageCards
pos_fn = html.find('async function loadTokensAndPages')
print("\n=== loadTokensAndPages ===")
print(html[pos_fn:pos_fn+1500])
