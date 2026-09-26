from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
for idx, l in enumerate(app_py.splitlines()):
    if "/api/groups" in l:
        print(f"Line {idx+1}: {l}")
        for j in range(max(0, idx-2), min(len(app_py.splitlines()), idx+25)):
            print(f"  {j+1}: {app_py.splitlines()[j]}")
        print("="*40)
