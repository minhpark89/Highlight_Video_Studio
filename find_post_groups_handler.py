from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

# Let's inspect where @app.route("/api/groups", methods=["POST"]) is defined
pos = text.find('@app.route("/api/groups", methods=["POST"])')
pos_end = text.find('@app.route', pos+10)
print("=== POST /api/groups ===")
print(text[pos:pos_end])
