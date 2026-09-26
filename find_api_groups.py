from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where page_manager is imported or initialized
for idx, l in enumerate(app_py.splitlines()[:60]):
    if "page_manager" in l or "database" in l or "PageManager" in l:
        print(f"{idx+1}: {l}")

# Check /api/groups routes
lines = app_py.splitlines()
for idx, l in enumerate(lines):
    if "/api/groups" in l:
        print(f"\nLine {idx+1}: {l}")
        for j in range(idx, min(len(lines), idx+25)):
            print(f"  {j+1}: {lines[j]}")
