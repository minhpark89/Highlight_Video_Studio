from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where editGroup or button with onclick for Sửa is created in loadLoHaGroups
pos_lg = html.find('async function loadLoHaGroups()')
print(html[pos_lg:pos_lg+2500])
