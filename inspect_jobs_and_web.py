import re

with open(r"D:\Highlight_Video_Studio\web\app.py", "r", encoding="utf-8") as f:
    text = f.read()

# Let's see how jobs and clips are stored
pos_jobs = text.find("load_jobs")
print("load_jobs snippet:\n", text[pos_jobs:pos_jobs+600])

# Let's see api_publish_website_article
pos_pub = text.find("def api_publish_website_article")
print("\napi_publish_website_article:\n", text[pos_pub:pos_pub+1200])
