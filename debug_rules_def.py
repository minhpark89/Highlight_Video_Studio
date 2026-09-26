from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
content = app_py.read_text(encoding="utf-8")

# Let's inspect handle_schedule_rules
pos = content.find("def handle_schedule_rules")
pos_end = content.find("@app.route", pos+10)
print("=== handle_schedule_rules ===")
print(content[pos:pos_end])

# Check what get_schedule_rules and save_schedule_rules are
print("Is get_schedule_rules defined?", "def get_schedule_rules" in content)
print("Is save_schedule_rules defined?", "def save_schedule_rules" in content)
