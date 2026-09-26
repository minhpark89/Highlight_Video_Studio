from pathlib import Path

# Check page_manager.py
for p in Path(r"D:\Highlight_Video_Studio").glob("**/*page*manager*.py"):
    txt = p.read_text(encoding="utf-8")
    print(f"=== {p} ===")
    pos = txt.find("def add_or_update_group")
    if pos != -1:
        print(txt[pos:pos+1000])
