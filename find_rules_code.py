from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect handle_schedule_rules
pos = app_py.find("def handle_schedule_rules")
print(app_py[pos:pos+1000])
