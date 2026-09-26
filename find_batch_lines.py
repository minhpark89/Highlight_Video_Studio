from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
lines = app_py.splitlines()

# Search for api_distribute_batch
for idx, l in enumerate(lines):
    if "api_distribute_batch" in l:
        print(f"Line {idx+1}: {l}")
        for j in range(idx, min(len(lines), idx+80)):
            print(f"  {j+1}: {lines[j]}")
        break
