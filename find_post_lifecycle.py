from pathlib import Path

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where scheduled posts in posts.json are actually published
# Look for posts.json or load_posts
lines = app_text.splitlines()
matches = []
for idx, l in enumerate(lines):
    if 'load_posts' in l or 'save_posts' in l:
        matches.append((idx+1, l))

print("Occurrences of load_posts / save_posts:")
for m in matches:
    print(m)
