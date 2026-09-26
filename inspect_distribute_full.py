from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Find api_distribute_batch
pos = app_py.find("def api_distribute_batch():")
pos_end = app_py.find("@app.route", pos+10)
print("=== api_distribute_batch in web/app.py ===")
print(app_py[pos:pos_end])
