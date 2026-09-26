from pathlib import Path
import re

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where "Xem trọn vẹn bản full" is in index.html or app.py
pos = html.find('Xem trọn vẹn bản full')
print("In index.html:", pos)
if pos != -1:
    print(html[pos-100:pos+300])

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
pos_app = app_text.find('Xem trọn vẹn')
print("In app.py:", pos_app)
if pos_app != -1:
    print(app_text[pos_app-100:pos_app+300])
