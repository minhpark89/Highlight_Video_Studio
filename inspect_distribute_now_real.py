from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

# Let's inspect api_distribute_batch completely
pos = text.find("def api_distribute_batch():")
pos_end = text.find("def handle_schedule_rules():", pos)
print("api_distribute_batch snippet:")
print(text[pos:pos+2500])
