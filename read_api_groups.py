from pathlib import Path

txt = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
pos = txt.find('@app.route("/api/groups", methods=["POST"])')
print(txt[pos:pos+700])
