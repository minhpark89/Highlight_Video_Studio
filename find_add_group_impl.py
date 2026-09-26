from pathlib import Path

# Search for "def add_or_update_group" in D:\Highlight_Video_Studio
for p in Path(r"D:\Highlight_Video_Studio").glob("**/*.py"):
    if 'venv' in str(p): continue
    try:
        txt = p.read_text(encoding="utf-8")
        if "add_or_update_group" in txt:
            print(f"File: {p}")
            pos = txt.find("def add_or_update_group")
            if pos != -1:
                print(txt[pos:pos+700])
    except Exception:
        pass
