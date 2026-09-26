from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
print("post_fb_id in index.html:", "post_fb_id" in html)
pos = html.find('post_fb_id')
while pos != -1:
    print(html[pos-50:pos+200])
    pos = html.find('post_fb_id', pos+1)
