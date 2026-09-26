from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

print("editGroupModal in index.html:", "function editGroupModal" in html)
pos = html.find("editGroupModal")
while pos != -1:
    print("Match at pos:", pos, html[pos-50:pos+100])
    pos = html.find("editGroupModal", pos+1)
