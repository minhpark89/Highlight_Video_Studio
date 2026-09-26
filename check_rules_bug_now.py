from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect handle_schedule_rules
pos = app_py.find("def handle_schedule_rules")
print(app_py[pos:pos+500])

# Search for get_schedule_rules or save_schedule_rules
print("get_schedule_rules in app_py:", "get_schedule_rules" in app_py)
