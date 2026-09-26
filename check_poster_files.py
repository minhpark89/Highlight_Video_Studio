import sys
from pathlib import Path

# Check reel_poster in Highlight_Video_Studio
for p in Path(r"D:\Highlight_Video_Studio").glob("**/*poster*.py"):
    print("Found poster file:", p)
    try:
        txt = p.read_text(encoding="utf-8")
        print(f"Lines in {p.name}: {len(txt.splitlines())}")
        for l in txt.splitlines()[:25]:
            print("  ", l)
    except Exception as e:
        print("  Error:", e)
