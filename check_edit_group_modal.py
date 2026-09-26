from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect openEditGroupModal in index.html
pos = html.find('function openEditGroupModal')
if pos != -1:
    print(html[pos:pos+1500])
else:
    pos_m = html.find('id="modal-edit-group"')
    print("modal-edit-group pos:", pos_m)
    # search where edit button is bound
    pos_btn = html.find('editGroup(')
    if pos_btn == -1: pos_btn = html.find('openEditGroup(')
    print("edit button pos:", pos_btn)
