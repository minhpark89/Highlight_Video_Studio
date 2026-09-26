from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
pos = app_py.find("def handle_schedule_rules")
print(app_py[pos:pos+600])
