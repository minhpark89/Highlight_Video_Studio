from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where runLoHaBatchSchedule is defined and why it might be overridden by an older definition
pos = html.rfind("async function runLoHaBatchSchedule")
if pos != -1:
    print("=== Last runLoHaBatchSchedule def ===")
    print(html[pos:pos+1500])

pos_first = html.find("async function runLoHaBatchSchedule")
print("\n=== First runLoHaBatchSchedule def ===")
print(html[pos_first:pos_first+1500])
