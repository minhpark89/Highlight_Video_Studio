from pathlib import Path

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

pos = text.find('render_template')
print("render_template at:", pos)
if pos != -1:
    print(text[pos-100:pos+300])

pos_idx = text.find('def index')
print("def index at:", pos_idx)
if pos_idx != -1:
    print(text[pos_idx:pos_idx+400])
