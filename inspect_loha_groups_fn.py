from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's inspect loadLoHaGroups function in index.html
pos = html.find('async function loadLoHaGroups')
pos_end = html.find('async function runLoHaBatchSchedule', pos)
print("=== loadLoHaGroups code ===")
print(html[pos:pos_end])
