from pathlib import Path

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

# Let's inspect the first 30 lines of app.py
lines = text.splitlines()
for i, l in enumerate(lines[:30]):
    print(f"{i+1}: {l}")
