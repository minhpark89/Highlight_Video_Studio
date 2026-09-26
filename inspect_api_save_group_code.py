from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

pos = text.find('def api_save_group')
pos_end = text.find('@app.route', pos+10)
print("=== api_save_group in app.py ===")
print(text[pos:pos_end])
