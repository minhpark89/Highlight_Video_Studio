import requests
import inspect
from pathlib import Path

# Check app.py route "/"
app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
pos = app_text.find('@app.route("/")')
print(app_text[pos:pos+400])

# Check template folder
pos_flask = app_text.find("app = Flask(")
print(app_text[pos_flask:pos_flask+200])
