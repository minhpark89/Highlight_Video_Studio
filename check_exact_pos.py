from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
print("modal-edit-group pos:", html.find('id="modal-edit-group"'))
print("edit-group-id pos:", html.find('id="edit-group-id"'))
