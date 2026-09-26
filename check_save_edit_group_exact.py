from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
pos = html.find("async function saveEditGroup")
pos_end = html.find("function runLoHaBatchSchedule", pos)
print(html[pos:pos_end])
