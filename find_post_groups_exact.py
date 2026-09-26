from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

# Let's inspect where /api/groups is defined
pos = text.find('@app.route("/api/groups", methods=["POST"])')
print("=== POST /api/groups ===")
print(text[pos:pos+800])
