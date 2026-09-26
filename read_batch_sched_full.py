from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect runLoHaBatchSchedule
pos = html.find('function runLoHaBatchSchedule(')
if pos == -1: pos = html.find('async function runLoHaBatchSchedule(')
print(html[pos:pos+2000])
