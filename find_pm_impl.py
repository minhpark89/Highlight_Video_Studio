from pathlib import Path

# Search for "def add_or_update_group" in D:\Highlight_Video_Studio
for p in Path(r"D:\Highlight_Video_Studio").glob("**/*.py"):
    if 'venv' in str(p): continue
    try:
        txt = p.read_text(encoding="utf-8")
        if "add_or_update_group" in txt:
            print(f"=== {p} ===")
            for idx, line in enumerate(txt.splitlines()):
                if "def add_or_update_group" in line or "class PageManager" in line:
                    for j in range(max(0, idx-2), min(len(txt.splitlines()), idx+35)):
                        print(f"{j+1}: {txt.splitlines()[j]}")
    except Exception:
        pass
