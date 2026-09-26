from pathlib import Path

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

# Let's inspect where background worker is started in app.py
# Look for _queue_thread
pos = text.find('_queue_thread = threading.Thread')
print("Found _queue_thread at pos:", pos)
if pos != -1:
    print(text[pos-100:pos+300])
