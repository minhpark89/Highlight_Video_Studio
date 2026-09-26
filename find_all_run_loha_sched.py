from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect runLoHaBatchSchedule in index.html
pos = 0
while True:
    pos = html.find('function runLoHaBatchSchedule', pos)
    if pos == -1: break
    print("Found definition at pos:", pos)
    print(html[pos:pos+600])
    print("="*40)
    pos += 30
