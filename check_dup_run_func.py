from pathlib import Path

# Let's inspect line 5030 to 5090 in templates/index.html to see the duplicate runLoHaBatchSchedule
html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
lines = html.splitlines()

for i in range(5030, min(len(lines), 5090)):
    print(f"{i+1}: {lines[i]}")
