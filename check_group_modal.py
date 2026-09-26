from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect modal-add-group or modal-group
pos = html.find('id="modal-add-group"')
if pos == -1: pos = html.find('id="modal-group"')
print("modal pos:", pos)
if pos != -1:
    print(html[pos:pos+1500])
