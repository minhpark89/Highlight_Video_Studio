from pathlib import Path

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where posts are processed or if a background thread executes posts
matches = [line for line in app_text.splitlines() if 'scheduled' in line.lower() or 'publish_reel' in line.lower()]
print(f"Matches ({len(matches)}):")
for m in matches[:30]:
    print(m)
