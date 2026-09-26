from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

pos = text.find("def handle_schedule_rules():")
pos_end = text.find("@app.route", pos+10)
print("=== handle_schedule_rules ===")
print(text[pos:pos_end])
