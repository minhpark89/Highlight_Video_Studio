from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect handle_schedule_rules and get_schedule_rules
pos = app_py.find("def handle_schedule_rules")
print("=== handle_schedule_rules ===")
print(app_py[pos:pos+400])

# Where is get_schedule_rules or save_schedule_rules defined?
print("\nIs get_schedule_rules defined?", "def get_schedule_rules" in app_py)
print("Is save_schedule_rules defined?", "def save_schedule_rules" in app_py)
