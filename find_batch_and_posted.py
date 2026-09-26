from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

matches = [m.start() for m in re.finditer(r"def api_distribute_batch", app_py)]
print("All occurrences of 'def api_distribute_batch' in app.py:", matches)
for m in matches:
    print(f"--- Pos {m} ---")
    print(app_py[m:m+600])

# Also check all occurrences of posted_clips in app.py
print("\nAll occurrences of posted_clips in app.py:")
for idx, l in enumerate(app_py.splitlines()):
    if "posted_clips" in l:
        print(f"Line {idx+1}: {l}")
