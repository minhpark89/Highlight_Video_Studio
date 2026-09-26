from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where groups are saved in app.py
lines = app_py.splitlines()
for idx, l in enumerate(lines):
    if "api_save_group" in l or "add_or_update_group" in l:
        print(f"Line {idx+1}: {l}")
        for j in range(max(0, idx-2), min(len(lines), idx+30)):
            print(f"  {j+1}: {lines[j]}")
        print("="*40)
