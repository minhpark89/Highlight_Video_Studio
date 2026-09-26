from pathlib import Path

# Search for posted_clips in all python files
base = Path(r"D:\Highlight_Video_Studio")
for p in base.glob("**/*.py"):
    if 'venv' in str(p): continue
    try:
        txt = p.read_text(encoding="utf-8")
        if "posted_clips" in txt:
            print(f"Found in {p.relative_to(base)}:")
            for idx, l in enumerate(txt.splitlines()):
                if "posted_clips" in l:
                    print(f"  {idx+1}: {l}")
    except Exception:
        pass
