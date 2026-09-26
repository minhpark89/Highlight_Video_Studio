from pathlib import Path

# Let's inspect D:\Highlight_Video_Studio to see where post publishing functions or modules are
p = Path(r"D:\Highlight_Video_Studio")
for f in p.glob("**/*.py"):
    if 'venv' in str(f) or '.git' in str(f): continue
    try:
        txt = f.read_text(encoding="utf-8")
        if 'graph.facebook.com' in txt or 'video_reels' in txt or 'publish_reel' in txt:
            print("Found Facebook publish logic in:", f.relative_to(p))
    except Exception:
        pass
