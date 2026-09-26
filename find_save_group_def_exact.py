from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's see lines around api_save_group
lines = app_py.splitlines()
for idx, l in enumerate(lines):
    if "api_save_group" in l or "/api/groups" in l:
        print(f"Line {idx+1}: {l}")
        for j in range(idx, min(len(lines), idx+25)):
            print(f"  {j+1}: {lines[j]}")
        print("="*40)
