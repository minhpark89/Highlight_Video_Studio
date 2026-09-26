from pathlib import Path
import re

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

# Let's inspect queue_worker_loop in app.py to see how background jobs are run
pos = text.find('def queue_worker_loop')
print(text[pos:pos+1500])
