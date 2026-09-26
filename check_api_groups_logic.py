from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's see how POST /api/groups is handled in app.py
pos = app_py.find('@app.route("/api/groups", methods=["POST"])')
print("=== POST /api/groups in app.py ===")
print(app_py[pos:pos+1000])
