from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where runLoHaBatchSchedule is in index.html
pos = 0
matches = []
while True:
    pos = html.find("function runLoHaBatchSchedule", pos)
    if pos == -1: break
    print(f"Match at pos {pos}:")
    print(html[pos:pos+500])
    print("="*40)
    pos += 30
