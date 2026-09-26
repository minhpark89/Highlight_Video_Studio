from pathlib import Path

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

# Let's inspect where posts are processed or published
# Search for posts.json or load_posts
pos = 0
matches = []
while True:
    pos = app_text.find('load_posts()', pos)
    if pos == -1: break
    line_no = app_text[:pos].count('\n') + 1
    matches.append(line_no)
    pos += 12

print("load_posts() line numbers:", matches)

# Check publish_reel endpoint
pos_pub = app_text.find('def api_publish_reel')
print("api_publish_reel pos:", pos_pub)
if pos_pub != -1:
    print(app_text[pos_pub:pos_pub+1500])
