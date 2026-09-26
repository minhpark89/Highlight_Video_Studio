from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
lines = app_py.splitlines()

# Search for api_distribute_batch
for idx, l in enumerate(lines):
    if "def api_distribute_batch" in l:
        print(f"Found api_distribute_batch at line {idx+1}")
        for j in range(idx, min(len(lines), idx+85)):
            print(f"{j+1}: {lines[j]}")
        break
