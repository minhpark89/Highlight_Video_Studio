from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's see the full code of api_distribute_batch
pos = app_py.find("def api_distribute_batch():")
pos_end = app_py.find("def handle_schedule_rules():", pos)
print("=== api_distribute_batch in web/app.py ===")
print(app_py[pos:pos_end])
