from pathlib import Path

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where scheduled posts in posts.json are posted by a background worker!
# Is there a loop that checks posts and calls reel_poster.publish_reel?
has_worker = "def scheduled_post_worker" in app_text or "def background_post" in app_text or "def check_scheduled_posts" in app_text
print("Has scheduled post worker in app.py?", has_worker)

# Let's search all while True in app.py
lines = app_text.splitlines()
for idx, l in enumerate(lines):
    if 'while True' in l or 'threading.Thread' in l:
        print(f"Line {idx+1}: {l}")
