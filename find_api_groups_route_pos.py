from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where /api/groups is defined
pos = app_py.find('@app.route("/api/groups", methods=["POST"])')
if pos == -1: pos = app_py.find('/api/groups')
print("Found at pos:", pos)
print(app_py[pos:pos+800])
