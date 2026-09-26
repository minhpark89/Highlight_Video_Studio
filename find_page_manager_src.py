import sys
from pathlib import Path

# Let's inspect where page_manager is implemented
for p in Path(r"D:\Highlight_Video_Studio").glob("**/*page*manager*.py"):
    print("Found page manager:", p)
    txt = p.read_text(encoding="utf-8")
    for idx, l in enumerate(txt.splitlines()[:50]):
        if "def add_or_update" in l or "def save" in l or "class " in l:
            print(f"Line {idx+1}: {l}")
    pos = txt.find("def add_or_update_group")
    if pos != -1:
        print("\n=== add_or_update_group ===")
        print(txt[pos:pos+700])
