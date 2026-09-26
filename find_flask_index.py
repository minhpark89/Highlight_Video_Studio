from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where app serves index
pos = app_py.find('def index')
if pos == -1: pos = app_py.find('render_template')
print("index route in app.py:\n", app_py[pos-50:pos+300])

# Where is template_folder defined in Flask?
pos_flask = app_py.find('Flask(')
print("\nFlask init:\n", app_py[pos_flask:pos_flask+300])
