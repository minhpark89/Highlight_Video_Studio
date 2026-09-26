with open(r"D:\Highlight_Video_Studio\web\app.py", "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("def api_distribute_batch")
pos_end = text.find("SCHEDULE_RULES_FILE", pos)
print("=== CURRENT api_distribute_batch ===")
print(text[pos:pos_end])
