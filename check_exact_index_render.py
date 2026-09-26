from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
for idx, l in enumerate(app_py.splitlines()):
    if 'render_template' in l or 'send_from_directory' in l:
        print(f"{idx+1}: {l}")

pos = app_py.find('@app.route("/")')
print("\n" + app_py[pos:pos+300])
