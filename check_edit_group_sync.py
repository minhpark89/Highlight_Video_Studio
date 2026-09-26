from pathlib import Path
import re

html_tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
html_web = Path(r"D:\Highlight_Video_Studio\web\index.html").read_text(encoding="utf-8")

print("edit-group-id in templates?", "id=\"edit-group-id\"" in html_tmpl)
print("edit-group-id in web/index.html?", "id=\"edit-group-id\"" in html_web)

# Let's inspect editGroupModal function in both files
def find_fn(txt):
    p = txt.find("async function editGroupModal")
    return txt[p:p+600] if p != -1 else "NOT FOUND"

print("\n--- templates/index.html fn ---\n", find_fn(html_tmpl))
print("\n--- web/index.html fn ---\n", find_fn(html_web))
