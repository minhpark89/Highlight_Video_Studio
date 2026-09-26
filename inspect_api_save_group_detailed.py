from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's see where api_save_group is in app.py
pos = app_py.find("def api_save_group")
print(app_py[pos:pos+800])
