from pathlib import Path

# Search where posted_clips.json is written or appended
base = Path(r"D:\Highlight_Video_Studio")
for p in base.glob("**/*.py"):
    if 'venv' in str(p): continue
    try:
        txt = p.read_text(encoding="utf-8")
        if "posted_clips.json" in txt and ("write" in txt or "dump" in txt or "open(" in txt):
            print(f"File {p.relative_to(base)} writes to posted_clips.json:")
            for idx, l in enumerate(txt.splitlines()):
                if "posted_clips" in l and ("write" in l or "dump" in l or "append" in l):
                    print(f"  {idx+1}: {l}")
    except Exception:
        pass
