from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect openEditGroupModal or whatever function is called when clicking "Sửa"
pos = html.find('openEditGroupModal')
if pos == -1: pos = html.find('editGroup')
print("editGroup pos:", pos)

# Find table row rendering for groups in loadLoHaGroups
pos_lg = html.find('async function loadLoHaGroups()')
print(html[pos_lg:pos_lg+1500])
