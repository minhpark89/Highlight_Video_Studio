from pathlib import Path

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's see lines 1330 to 1430 in app.py where api_distribute_batch is
lines = app_text.splitlines()
for i in range(1320, min(len(lines), 1435)):
    print(f"{i+1}: {lines[i]}")
