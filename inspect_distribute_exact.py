from pathlib import Path

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

# Let's inspect api_distribute_batch and surrounding code
pos = text.find("def api_distribute_batch():")
pos_end = text.find("SCHEDULE_RULES_FILE", pos)

print("=== CURRENT DISTRIBUTE BATCH ===")
print(text[pos:pos_end])
