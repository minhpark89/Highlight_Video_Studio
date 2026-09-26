from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
print("modal-edit-group in templates/index.html?", "modal-edit-group" in html)

# Let's search where modal-edit-group is in templates/index.html
pos = html.find('id="modal-edit-group"')
print("pos of modal-edit-group:", pos)
if pos != -1:
    print(html[pos:pos+500])
else:
    # search modal-edit
    pos2 = html.find('modal-edit')
    print("modal-edit pos:", pos2)
