from pathlib import Path
import re

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect all definitions of runLoHaBatchSchedule in index.html
pos = 0
matches = []
while True:
    pos = html.find('runLoHaBatchSchedule', pos)
    if pos == -1: break
    line_no = html[:pos].count('\n') + 1
    matches.append((pos, line_no))
    pos += 20

print("Matches of runLoHaBatchSchedule in index.html:")
for pos, l in matches:
    print(f"Line {l}: {html[pos-30:pos+150]}")
    print("-" * 40)
