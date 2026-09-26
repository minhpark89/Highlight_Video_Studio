from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

pos_lg = html.find('async function loadLoHaGroups()')
pos_end = html.find('tbody.innerHTML = rows;', pos_lg)
snippet = html[pos_lg:pos_end+50]

for line in snippet.splitlines():
    if 'Sửa' in line or 'onclick' in line or '<button' in line:
        print(line)
