from pathlib import Path

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
lines = app_text.splitlines()

for i, l in enumerate(lines):
    if "first_comm =" in l or "article_url =" in l:
        print(f"Line {i+1}: {l}")
        for j in range(max(0, i-2), min(len(lines), i+15)):
            print(f"  {j+1}: {lines[j]}")
