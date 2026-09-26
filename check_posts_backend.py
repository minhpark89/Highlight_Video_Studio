with open('D:/Highlight_Video_Studio/web/app.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
# check load_posts and save_posts
for fn in ['def load_posts', 'def save_posts', 'def load_jobs', 'POSTS_FILE']:
    pos = text.find(fn)
    print(fn, "at", pos)
    if pos != -1:
        print(text[pos:pos+300])
        print("---")
