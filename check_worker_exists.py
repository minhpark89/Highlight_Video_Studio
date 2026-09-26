from pathlib import Path

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's search for how posts in posts.json are published
has_sched_worker = "def scheduled_post_worker" in app_text or "def post_worker" in app_text or "scheduler" in app_text
print("Has scheduled worker in app.py?", has_sched_worker)

# Let's inspect all threading in app.py
import re
for m in re.finditer(r'threading\.Thread\([^)]+\)', app_text):
    print(m.group(0))
