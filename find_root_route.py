from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where render_template or send_from_directory is called for index
pos = app_py.find('@app.route("/")')
print(app_py[pos:pos+500])
