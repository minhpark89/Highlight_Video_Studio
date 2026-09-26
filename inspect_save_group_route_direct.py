from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where /api/groups is defined
pos = app_py.find('api_save_group')
print(app_py[pos-100:pos+800])
