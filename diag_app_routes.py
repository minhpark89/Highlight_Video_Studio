from pathlib import Path

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

# Let's inspect lines around /api/posts in app.py
lines = text.splitlines()
for idx, l in enumerate(lines):
    if '/api/posts' in l:
        for j in range(max(0, idx-3), min(len(lines), idx+15)):
            print(f"{j+1}: {lines[j]}")
        print("="*40)
