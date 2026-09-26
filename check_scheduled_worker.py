with open(r"D:\Highlight_Video_Studio\web\app.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = re.findall(r'def\s+.*publish|MetaReelPoster|background_thread|schedule_worker', text, re.IGNORECASE)
print("Matches in app.py:", matches)

# Check if there is an existing worker that checks scheduled posts and publishes them
pos = text.find("def api_publish_reel")
if pos != -1:
    print("api_publish_reel code snippet:")
    print(text[pos:pos+1200])
