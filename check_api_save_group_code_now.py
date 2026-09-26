from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect /api/groups POST handler
pos = app_py.find('def api_save_group')
pos_end = app_py.find('@app.route', pos+10)
print("=== api_save_group in app.py ===")
print(app_py[pos:pos_end])
