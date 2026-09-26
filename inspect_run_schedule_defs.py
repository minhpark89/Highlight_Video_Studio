from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect runLoHaBatchSchedule in index.html
pos = html.find('async function runLoHaBatchSchedule')
print("=== async function runLoHaBatchSchedule ===")
print(html[pos:pos+1500])

pos2 = html.find('function runLoHaBatchSchedule')
print("\n=== function runLoHaBatchSchedule ===")
print(html[pos2:pos2+1500])
