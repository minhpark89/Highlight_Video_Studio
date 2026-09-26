from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's see how groups are handled in app.py
# Search for page_groups.json
for idx, l in enumerate(app_py.splitlines()):
    if "page_groups.json" in l or "list_groups" in l or "save_group" in l or "add_or_update_group" in l:
        print(f"Line {idx+1}: {l}")
