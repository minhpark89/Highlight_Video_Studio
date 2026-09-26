from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
pos = app_py.find("def api_distribute_batch")
pos_end = app_py.find("@app.route", pos+20)
if pos_end == -1: pos_end = pos + 4000

print(app_py[pos:pos_end])
