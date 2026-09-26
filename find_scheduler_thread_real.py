from pathlib import Path
import re

text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where scheduled posts are published or if there is a scheduler thread
for idx, line in enumerate(text.splitlines()):
    if 'scheduled' in line.lower() or 'run_pending' in line.lower() or 'publish_scheduled' in line.lower() or 'scheduler' in line.lower():
        print(f"{idx+1}: {line}")
