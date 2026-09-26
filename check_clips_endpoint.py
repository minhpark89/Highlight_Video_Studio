with open("D:/Highlight_Video_Studio/web/app.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
idx = text.find('route("/api/clips"')
if idx == -1:
    idx = text.find("route('/api/clips'")
print(text[idx-20:idx+800])
