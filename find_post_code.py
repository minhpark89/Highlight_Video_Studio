import os
from pathlib import Path

base = Path(r"D:\Highlight_Video_Studio")
for p in base.glob("**/*.py"):
    if 'venv' in str(p): continue
    try:
        txt = p.read_text(encoding="utf-8")
        if 'scheduled' in txt and ('publish' in txt or 'graph' in txt or 'facebook' in txt):
            print(f"Found match in: {p.relative_to(base)}")
    except Exception:
        pass
