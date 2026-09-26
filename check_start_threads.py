from pathlib import Path

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

# Let's inspect where queue background thread is started:
# Search for _queue_thread
pos = text.find('_queue_thread')
print(text[pos-100:pos+300])
