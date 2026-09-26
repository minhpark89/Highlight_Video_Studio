from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

# Let's inspect api_save_group in app.py
pos = text.find('def api_save_group')
print(text[pos:pos+700])
