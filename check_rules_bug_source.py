from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
content = app_py.read_text(encoding="utf-8")

# Let's inspect handle_schedule_rules
pos = content.find("def handle_schedule_rules():")
pos_end = content.find("@app.route", pos+10)
print("=== handle_schedule_rules ===")
print(content[pos:pos_end])
