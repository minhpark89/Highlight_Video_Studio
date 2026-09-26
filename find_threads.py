from pathlib import Path

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's search where background loop or scheduler is started
pos = app_text.find('def background_')
if pos == -1: pos = app_text.find('def schedule_')
if pos == -1: pos = app_text.find('Thread(target=')
while pos != -1:
    print(app_text[pos:pos+300])
    print("="*40)
    pos = app_text.find('Thread(target=', pos+1)
