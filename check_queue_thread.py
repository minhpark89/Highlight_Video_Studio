from pathlib import Path

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

# Let's inspect where queue_thread is started in app.py
pos = text.find('_queue_thread = threading.Thread')
print(text[pos-100:pos+300])
