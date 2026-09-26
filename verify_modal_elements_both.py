from pathlib import Path
import re

html_tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
html_web = Path(r"D:\Highlight_Video_Studio\web\index.html").read_text(encoding="utf-8")

def check_file(path_name, content):
    print(f"=== {path_name} (Length: {len(content)}) ===")
    print("modal-edit-group:", 'id="modal-edit-group"' in content)
    print("edit-group-id:", 'id="edit-group-id"' in content)
    print("edit-group-name:", 'id="edit-group-name"' in content)
    print("edit-group-folder:", 'id="edit-group-folder"' in content)
    print("edit-group-times:", 'id="edit-group-times"' in content)
    print("edit-group-stagger:", 'id="edit-group-stagger"' in content)
    print("edit-group-pages-list:", 'id="edit-group-pages-list"' in content)
    print("edit-group-page-count:", 'id="edit-group-page-count"' in content)

check_file("templates/index.html", html_tmpl)
check_file("web/index.html", html_web)
