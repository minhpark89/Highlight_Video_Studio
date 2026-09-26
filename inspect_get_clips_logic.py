from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
pos = app_py.find("def get_all_clips()")
print(app_py[pos:pos+1500])
