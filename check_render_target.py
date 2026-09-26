from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's find index route
pos = app_py.find('def index')
if pos == -1: pos = app_py.find('render_template')
print(app_py[pos-50:pos+300])
