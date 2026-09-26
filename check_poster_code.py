from pathlib import Path

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's see how reel_poster is imported and used in app.py
lines = app_text.splitlines()
for idx, l in enumerate(lines[:60]):
    if 'poster' in l.lower() or 'reel' in l.lower():
        print(f"Line {idx+1}: {l}")

# Check api_publish_reel
pos = app_text.find('def api_publish_reel')
print(app_text[pos:pos+1200])
