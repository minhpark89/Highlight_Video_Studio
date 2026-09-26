from pathlib import Path

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

# Let's inspect where queue_worker_loop or background threads are
pos = text.find('def queue_worker_loop')
print(text[pos:pos+1500])
