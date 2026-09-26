from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect POST /api/groups in app.py
pos = app_py.find('@app.route("/api/groups", methods=["POST"])')
pos_end = app_py.find('@app.route', pos+10)
print("=== POST /api/groups ===")
print(app_py[pos:pos_end])
