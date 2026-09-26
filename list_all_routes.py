from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
for idx, l in enumerate(app_py.splitlines()):
    if '@app.route' in l:
        print(f"Line {idx+1}: {l}")
