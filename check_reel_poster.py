from pathlib import Path
import re

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

# Let's inspect where scheduled_posts background thread should be added
# In app.py, there is a reel_poster module! Let's check how reel_poster works
pos = text.find('reel_poster')
while pos != -1:
    print(text[pos-50:pos+150])
    pos = text.find('reel_poster', pos+1)
    if pos > 3000: break
