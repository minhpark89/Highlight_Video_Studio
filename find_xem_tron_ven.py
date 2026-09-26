import os
from pathlib import Path

base = Path(r"D:\Highlight_Video_Studio")
for p in base.glob("**/*.*"):
    if 'venv' in str(p) or '.git' in str(p): continue
    if p.suffix in ['.py', '.html', '.js']:
        try:
            txt = p.read_text(encoding="utf-8")
            if "Xem trọn vẹn" in txt:
                print("Found 'Xem trọn vẹn' in:", p.relative_to(base))
        except Exception:
            pass
