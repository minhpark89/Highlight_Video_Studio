from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where groups are saved or updated in app.py
lines = app_py.splitlines()
matches = [idx for idx, l in enumerate(lines) if 'def api_save_group' in l or 'add_or_update_group' in l or 'api_delete_group' in l]
print("Matches in app.py:", matches)
for m in matches:
    for j in range(max(0, m-2), min(len(lines), m+25)):
        print(f"{j+1}: {lines[j]}")
    print("="*40)
