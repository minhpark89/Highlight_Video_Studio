from pathlib import Path

# Search for page_groups.json or list_groups in all files
for p in Path(r"D:\Highlight_Video_Studio").glob("**/*.py"):
    if 'venv' in str(p): continue
    try:
        txt = p.read_text(encoding="utf-8")
        if "page_groups.json" in txt:
            print(f"Found page_groups.json in {p}:")
            for idx, l in enumerate(txt.splitlines()):
                if "page_groups.json" in l or "add_or_update_group" in l or "delete_group" in l:
                    print(f"  {idx+1}: {l}")
    except Exception:
        pass
