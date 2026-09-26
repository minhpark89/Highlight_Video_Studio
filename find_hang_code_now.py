from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's search for "Đang nạp danh sách Fanpage"
pos = html.find("Đang nạp danh sách Fanpage")
print("Found text at:", pos)
if pos != -1:
    print(html[pos-150:pos+350])
