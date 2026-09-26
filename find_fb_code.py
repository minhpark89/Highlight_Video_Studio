import os
from pathlib import Path

# Search for graph.facebook.com in all python files
base = Path(r"D:\Highlight_Video_Studio")
found = []
for p in base.rglob("*.py"):
    if "venv" in str(p): continue
    try:
        content = p.read_text(encoding="utf-8")
        if "graph.facebook.com" in content or "video_reels" in content:
            found.append(p)
    except Exception:
        pass

print("Files with facebook graph calls:", found)
for f in found:
    print(f"=== {f} ===")
    lines = f.read_text(encoding="utf-8").splitlines()
    for l in lines:
        if "graph.facebook.com" in l or "video_reels" in l or "comments" in l:
            print("  ", l)
