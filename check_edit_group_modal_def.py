from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Check if editGroupModal is defined in index.html
pos = html.find('editGroupModal')
print("editGroupModal occurrences:")
while pos != -1:
    print("Pos:", pos, html[pos-20:pos+80])
    pos = html.find('editGroupModal', pos+1)
