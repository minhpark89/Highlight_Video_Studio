from pathlib import Path

text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
lines = text.splitlines()
for idx, line in enumerate(lines):
    if '/api/posts' in line:
        print(f"Line {idx+1}: {line}")
        for j in range(max(0, idx-2), min(len(lines), idx+10)):
            print(f"  {j+1}: {lines[j]}")
