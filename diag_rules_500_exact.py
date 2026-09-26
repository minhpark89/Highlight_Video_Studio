from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

pos = app_py.find("def get_schedule_rules")
if pos != -1:
    print(app_py[pos:pos+600])
else:
    print("def get_schedule_rules not found!")

# Let's see how handle_schedule_rules is defined
pos_h = app_py.find("def handle_schedule_rules")
print("\n=== handle_schedule_rules ===")
print(app_py[pos_h:pos_h+600])
