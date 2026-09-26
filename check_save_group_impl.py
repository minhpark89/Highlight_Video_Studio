from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect api_save_group in app.py
pos = app_py.find("def api_save_group")
print(app_py[pos:pos+1000])

# Also check page_manager.add_or_update_group implementation
pos_pm = app_py.find("def add_or_update_group")
if pos_pm != -1:
    print("\nadd_or_update_group in app.py:\n", app_py[pos_pm:pos_pm+800])
