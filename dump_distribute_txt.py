from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

pos = text.find("def api_distribute_batch():")
pos_end = text.find("def handle_schedule_rules():", pos)

with open(r"D:\Highlight_Video_Studio\distribute_dump.txt", "w", encoding="utf-8") as f:
    f.write(text[pos:pos_end])

print("Wrote distribute_dump.txt, length:", pos_end - pos)
