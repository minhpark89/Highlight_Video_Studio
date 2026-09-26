with open(r"D:\Highlight_Video_Studio\web\app.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
pos = text.find("def post_worker")
if pos == -1: pos = text.find("def background_publisher")
if pos == -1: pos = text.find("def publisher_thread")
if pos == -1: pos = text.find("MetaReelPoster")

print("Found publisher around:", pos)
if pos != -1:
    print(text[pos-100:pos+1500])
