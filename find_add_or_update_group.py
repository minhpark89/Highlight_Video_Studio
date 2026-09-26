from pathlib import Path

# Check where add_or_update_group is defined across the repo
for p in Path(r"D:\Highlight_Video_Studio").glob("**/*.py"):
    if 'venv' in str(p): continue
    try:
        txt = p.read_text(encoding="utf-8")
        if "def add_or_update_group" in txt:
            print("Found add_or_update_group in:", p)
            pos = txt.find("def add_or_update_group")
            print(txt[pos:pos+600])
    except Exception:
        pass
