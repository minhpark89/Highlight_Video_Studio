from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's search for posted_clips in app.py
for idx, l in enumerate(app_py.splitlines()):
    if "posted_clips" in l:
        print(f"Line {idx+1}: {l}")
