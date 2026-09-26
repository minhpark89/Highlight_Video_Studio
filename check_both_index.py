from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = tmpl.read_text(encoding="utf-8")

print("modal-edit-group in tmpl?", "modal-edit-group" in html)
pos = html.find('id="modal-edit-group"')
print("pos in tmpl:", pos)

web_idx = Path(r"D:\Highlight_Video_Studio\web\index.html")
html_web = web_idx.read_text(encoding="utf-8")
print("modal-edit-group in web_idx?", "modal-edit-group" in html_web)
pos_w = html_web.find('id="modal-edit-group"')
print("pos in web_idx:", pos_w)
