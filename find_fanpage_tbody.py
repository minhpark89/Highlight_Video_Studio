from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where "Đang nạp danh sách Fanpage Facebook" is in index.html
pos = html.find('Đang nạp danh sách Fanpage Facebook')
print("Position:", pos)
if pos != -1:
    print(html[pos-100:pos+300])

# Find the function that populates this table or grid
# In pane-pages, look for the tbody id
pos_tbody = html.rfind('<tbody', 0, pos)
print("tbody tag:", html[pos_tbody:pos_tbody+100])
