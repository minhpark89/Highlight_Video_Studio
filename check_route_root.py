from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's search for route "/"
pos = app_py.find('@app.route("/")')
print(app_py[pos:pos+400])
