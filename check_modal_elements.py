from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's check if modal-edit-group elements exist in index.html
elements = ['edit-group-id', 'edit-group-name', 'edit-group-folder', 'edit-group-times', 'edit-group-stagger', 'modal-edit-group', 'edit-group-pages-list', 'edit-group-page-count']

for el in elements:
    print(f"Element '{el}': in html? {f'id=\"{el}\"' in html}")
