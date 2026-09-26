from pathlib import Path
import re

html_tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
html_web = Path(r"D:\Highlight_Video_Studio\web\index.html").read_text(encoding="utf-8")

print("modal-edit-group in tmpl:", "id=\"modal-edit-group\"" in html_tmpl)
print("modal-edit-group in web_idx:", "id=\"modal-edit-group\"" in html_web)

pos_tmpl = html_tmpl.find('id="modal-edit-group"')
pos_web = html_web.find('id="modal-edit-group"')

print("pos in tmpl:", pos_tmpl)
print("pos in web_idx:", pos_web)
