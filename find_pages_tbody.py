from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where 'Đang nạp danh sách Fanpage Facebook' is
pos = html.find('Đang nạp danh sách Fanpage Facebook')
print("Position:", pos)
if pos != -1:
    print(html[pos-100:pos+300])

# What function renders into this container?
# Look for fb-page-cards-grid or pages-tbody or whatever container it is
pos_id = html.rfind('id=', 0, pos)
print("Container ID near pos:", html[pos_id:pos_id+50])

# Let's search where this container is updated in JavaScript
id_str = html[pos_id:pos_id+50].split('"')[1]
print("Target container ID:", id_str)

pos_js = html.find(f"getElementById('{id_str}')")
while pos_js != -1:
    print("JS match at:", pos_js)
    print(html[pos_js-50:pos_js+250])
    pos_js = html.find(f"getElementById('{id_str}')", pos_js+1)
