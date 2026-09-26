from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = tmpl.read_text(encoding="utf-8")

print("modal-edit-group in tmpl?", "id=\"modal-edit-group\"" in html)
print("edit-group-id in tmpl?", "id=\"edit-group-id\"" in html)

web_idx = Path(r"D:\Highlight_Video_Studio\web\index.html")
html_web = web_idx.read_text(encoding="utf-8")
print("modal-edit-group in web_idx?", "id=\"modal-edit-group\"" in html_web)
print("edit-group-id in web_idx?", "id=\"edit-group-id\"" in html_web)

# If not in tmpl, let's find why!
if "id=\"edit-group-id\"" not in html:
    print("WARNING: edit-group-id is missing from templates/index.html!")
