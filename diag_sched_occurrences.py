from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's find all occurrences of runLoHaBatchSchedule in index.html
pos = 0
while True:
    pos = html.find("runLoHaBatchSchedule", pos)
    if pos == -1: break
    print(f"--- pos {pos} ---")
    print(html[pos-30:pos+300])
    pos += 21
