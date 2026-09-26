from pathlib import Path

# Let's inspect saveEditGroup in web/templates/index.html
html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
pos = html.find("async function saveEditGroup")
print("saveEditGroup in index.html:\n", html[pos:pos+1000])

# Let's inspect backend /api/groups POST handler
app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
pos_api = app_py.find('@app.route("/api/groups", methods=["POST"])')
print("\nBackend /api/groups handler:\n", app_py[pos_api:pos_api+600])
