from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
pos = app_py.find("def handle_schedule_rules")
print("handle_schedule_rules in app.py:\n", app_py[pos:pos+400])

# Where is get_schedule_rules?
pos_g = app_py.find("get_schedule_rules")
while pos_g != -1:
    print(f"Match at {pos_g}:", app_py[pos_g-30:pos_g+100])
    pos_g = app_py.find("get_schedule_rules", pos_g+1)
