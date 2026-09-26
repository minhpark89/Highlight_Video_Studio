from pathlib import Path
import re

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where runLoHaBatchSchedule is in index.html
pos = 0
matches = []
while True:
    pos = html.find("runLoHaBatchSchedule", pos)
    if pos == -1: break
    line_no = html[:pos].count('\n') + 1
    matches.append((pos, line_no))
    pos += 20

print("Matches:", matches)
for pos, l in matches:
    print(f"Line {l}:")
    print(html[pos-20:pos+300])
    print("-" * 50)
