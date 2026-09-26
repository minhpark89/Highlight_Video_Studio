from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where the table button for Lên lịch calls runLoHaBatchSchedule
pos_tb = html.find('runLoHaBatchSchedule(')
while pos_tb != -1:
    print("Call in html:", html[pos_tb-50:pos_tb+150])
    pos_tb = html.find('runLoHaBatchSchedule(', pos_tb+1)

# Let's find definition of runLoHaBatchSchedule
pos_fn = html.find('function runLoHaBatchSchedule')
print("\nFirst def pos:", pos_fn)
pos_last = html.rfind('function runLoHaBatchSchedule')
print("Last def pos:", pos_last)
if pos_last != -1:
    print("\nLast definition:\n", html[pos_last:pos_last+1200])
