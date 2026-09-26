from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

# Let's inspect where api_distribute_batch is and how it creates articles / first comments
pos1 = text.find("def api_distribute_batch():")
pos2 = text.find("SCHEDULE_RULES_FILE", pos1)
print("=== api_distribute_batch slice ===")
print(text[pos1:pos2])
