from pathlib import Path

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where scheduled posts are published
pos = app_text.find('def background_')
if pos == -1: pos = app_text.find('def scheduler_')
if pos == -1: pos = app_text.find('def publish_post')
if pos == -1: pos = app_text.find('scheduled')

# Let's find any background thread checking posts.json
for idx, line in enumerate(app_text.splitlines()):
    if 'posts.json' in line or 'load_posts' in line:
        print(f"Line {idx}: {line}")
