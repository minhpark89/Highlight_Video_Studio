from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect loadLoHaGroups where buttons are rendered
pos_lg = html.find('async function loadLoHaGroups()')
pos_end = html.find('tbody.innerHTML = rows;', pos_lg)
print(html[pos_lg:pos_end+30])
