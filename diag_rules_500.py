from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

# Let's inspect handle_schedule_rules
pos = text.find("def handle_schedule_rules")
pos_end = text.find("@app.route", pos+10)
print("=== handle_schedule_rules in app.py ===")
print(text[pos:pos_end])
