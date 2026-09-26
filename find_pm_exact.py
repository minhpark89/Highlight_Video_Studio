from pathlib import Path

# Search for "class PageManager" across all python files
for p in Path(r"D:\Highlight_Video_Studio").glob("**/*.py"):
    if 'venv' in str(p): continue
    try:
        txt = p.read_text(encoding="utf-8")
        if "class PageManager" in txt or "page_manager = " in txt:
            print(f"=== {p} ===")
            pos = txt.find("add_or_update_group")
            if pos != -1:
                print(txt[pos:pos+600])
            else:
                pos2 = txt.find("save_group")
                if pos2 != -1:
                    print(txt[pos2:pos2+600])
    except Exception:
        pass
