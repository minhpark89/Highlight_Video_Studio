from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

# Let's inspect where api_distribute_batch is
pos_dist = text.find("def api_distribute_batch():")
pos_rules = text.find("SCHEDULE_RULES_FILE = BASE_DIR", pos_dist)

print("=== DISTRIBUTE BATCH CODE ===")
print(text[pos_dist:pos_rules])
