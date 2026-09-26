from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Search for "Đang nạp danh sách Fanpage Facebook"
pos = html.find("Đang nạp danh sách Fanpage Facebook")
print("Position:", pos)
if pos != -1:
    print(html[pos-150:pos+350])
