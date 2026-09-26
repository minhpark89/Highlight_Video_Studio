from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where "Đang nạp danh sách Fanpage Facebook..." is in index.html
pos = html.find('Đang nạp danh sách Fanpage Facebook')
print("Position:", pos)
if pos != -1:
    print(html[pos-120:pos+350])

# What JS function replaces this tbody?
# Search for pages-tbody
pos_tb = html.find("pages-tbody")
while pos_tb != -1:
    print("pages-tbody match at:", pos_tb)
    print(html[pos_tb-50:pos_tb+300])
    print("="*40)
    pos_tb = html.find("pages-tbody", pos_tb+1)
