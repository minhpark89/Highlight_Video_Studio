from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect /api/groups routes
lines = app_py.splitlines()
for idx, l in enumerate(lines):
    if "/api/groups" in l:
        print(f"Line {idx+1}: {l}")
        for j in range(idx, min(len(lines), idx+20)):
            print(f"  {j+1}: {lines[j]}")
