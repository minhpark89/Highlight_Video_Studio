from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

# Let's inspect where api_distribute_batch is
pos_dist = text.find("def api_distribute_batch():")
pos_rules = text.find("SCHEDULE_RULES_FILE = BASE_DIR", pos_dist)

code_snippet = text[pos_dist:pos_rules]
print("Lines in api_distribute_batch:", len(code_snippet.splitlines()))
print("\nFirst 40 lines:\n" + "\n".join(code_snippet.splitlines()[:40]))
print("\nLast 45 lines:\n" + "\n".join(code_snippet.splitlines()[-45:]))
