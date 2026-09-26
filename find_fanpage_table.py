from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where "Đang nạp danh sách Fanpage" appears in the template
pos = html.find("Đang nạp danh sách Fanpage")
print("Position:", pos)
if pos != -1:
    print(html[pos-200:pos+300])
