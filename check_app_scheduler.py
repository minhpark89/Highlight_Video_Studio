with open(r"D:\Highlight_Video_Studio\web\app.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = re.findall(r'def\s+.*scheduler|def\s+.*worker|def\s+.*publish|facebook_service|post_worker', text, re.IGNORECASE)
print("Publish / worker / scheduler functions in app.py:")
for m in set(matches):
    print(" -", m)

# Check if there is a background thread for scheduled posts
print("Has threading/scheduler for posts:", 'schedule' in text and 'threading' in text)
