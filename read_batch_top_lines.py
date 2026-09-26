from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

pos = text.find("def api_distribute_batch():")
pos_end = text.find("def handle_schedule_rules():", pos)
print("api_distribute_batch lines in app.py:")
lines = text[pos:pos_end].splitlines()
for i, l in enumerate(lines[:60]):
    print(f"{i+1}: {l}")
