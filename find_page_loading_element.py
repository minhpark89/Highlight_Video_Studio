from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where 'Đang nạp danh sách Fanpage Facebook' is
pos = html.find('Đang nạp danh sách Fanpage Facebook')
print("Position in html:", pos)
if pos != -1:
    print(html[pos-150:pos+350])

# What function renders into this container?
# Search for the container id or parent id
pos_tbody = html.rfind('id=', 0, pos)
print("Parent container near pos:", html[pos_tbody:pos_tbody+50])
