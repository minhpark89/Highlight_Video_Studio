from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

pos = text.find("def handle_schedule_rules")
pos_end = text.find("@app.route", pos+10)
print("=== handle_schedule_rules ===")
print(text[pos:pos_end])

pos_g = text.find("def get_schedule_rules")
print("\nIs get_schedule_rules in app.py?", pos_g != -1)
