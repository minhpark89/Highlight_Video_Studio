from pathlib import Path

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
lines = app_text.splitlines()

for i in range(1340, min(len(lines), 1450)):
    print(f"{i+1}: {lines[i]}")
