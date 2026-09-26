from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

pos = html.find('async function editGroupModal')
pos_end = html.find('function updateEditPageCount', pos)
print("=== editGroupModal ===")
print(html[pos:pos_end])
