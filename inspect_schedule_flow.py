from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

pos = html.find('function runLoHaBatchSchedule')
if pos == -1: pos = html.find('async function runLoHaBatchSchedule')
print("=== runLoHaBatchSchedule in templates/index.html ===")
print(html[pos:pos+1500])

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
pos_app = app_py.find('def api_distribute_batch')
pos_app_end = app_py.find('@app.route', pos_app+10)
print("\n=== api_distribute_batch in app.py ===")
print(app_py[pos_app:pos_app_end])
