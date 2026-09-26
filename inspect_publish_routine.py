from pathlib import Path
import re

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

# Let's inspect where queue_worker_loop is defined
pos = text.find('def queue_worker_loop')
print("queue_worker_loop pos:", pos)

# We need a background thread: scheduled_publisher_worker()
# Every 30 seconds:
# 1. load_posts()
# 2. Check posts with status == 'scheduled'
# 3. If scheduled_time <= now:
#    call publish function or Meta Graph API / reel_poster
# 4. Update status to 'published' (or 'failed') with post_id / fb_url / published_at
# 5. Save posts.json

# Let's see how api_publish_reel posts to Facebook
pos_pub = text.find('def api_publish_reel')
print(text[pos_pub:pos_pub+1200])
