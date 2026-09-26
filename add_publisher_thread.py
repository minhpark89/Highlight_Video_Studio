from pathlib import Path

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

# Let's inspect where queue_thread is started and add the scheduled_publisher thread
old_worker_start = """# Start queue background thread
_queue_thread = threading.Thread(target=queue_worker_loop, daemon=True)
_queue_thread.start()"""

new_worker_start = """# Start queue background thread
_queue_thread = threading.Thread(target=queue_worker_loop, daemon=True)
_queue_thread.start()

# Start scheduled posts publisher background thread (LoHa Page standard)
from web.scheduled_publisher import scheduled_publisher_worker_loop
_publisher_thread = threading.Thread(target=scheduled_publisher_worker_loop, daemon=True)
_publisher_thread.start()"""

if old_worker_start in text:
    text = text.replace(old_worker_start, new_worker_start)
    app_path.write_text(text, encoding="utf-8")
    print("Added _publisher_thread to app.py successfully!")
else:
    print("Could not find old_worker_start in app.py")
