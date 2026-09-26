from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where posts are rendered
pos = html.find('p.post_fb_id')
print("Found p.post_fb_id at:", pos)
if pos != -1:
    print(html[pos-100:pos+300])
else:
    # search where loadPostsTable is
    pos_fn = html.find('loadPostsTable')
    print("loadPostsTable pos:", pos_fn)
    print(html[pos_fn:pos_fn+1000])
