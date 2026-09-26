import re
from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

pos = text.find("def api_distribute_batch():")
pos_end = text.find("@app.route", pos+10)
print(text[pos:pos_end])
