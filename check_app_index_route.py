from pathlib import Path

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
pos = app_text.find('def index(')
if pos == -1: pos = app_text.find('def serve_index(')
if pos == -1: pos = app_text.find('@app.route("/")')
print(app_text[pos:pos+500])
