from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's see Flask app definition
pos_flask = app_py.find("app = Flask(")
print(app_py[pos_flask:pos_flask+400])

pos_index = app_py.find("def index():")
print(app_py[pos_index-50:pos_index+200])
