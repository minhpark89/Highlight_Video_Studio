from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

# Let's inspect api_save_group in app.py
pos = text.find('def api_save_group')
pos_end = text.find('@app.route', pos+10)
print("=== api_save_group ===")
print(text[pos:pos_end])

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
pos_js = html.find('async function saveEditGroup')
pos_js_end = html.find('function runLoHaBatchSchedule', pos_js)
print("\n=== saveEditGroup JS ===")
print(html[pos_js:pos_js_end])
