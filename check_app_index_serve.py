import os
from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect index() function in app.py
pos = app_py.find("def index()")
print(app_py[pos:pos+400])
