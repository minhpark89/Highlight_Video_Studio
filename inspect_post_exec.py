from pathlib import Path
import re

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

# Let's inspect where queue_worker_loop is defined
pos = text.find('def queue_worker_loop')
print("queue_worker_loop pos:", pos)
if pos != -1:
    print(text[pos:pos+600])

# Let's check how api_publish_reel publishes video
pos_pub = text.find('def api_publish_reel')
print("\napi_publish_reel pos:", pos_pub)
print(text[pos_pub:pos_pub+1200])
