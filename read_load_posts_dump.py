from pathlib import Path

txt = Path(r"D:\Highlight_Video_Studio\load_posts_body.txt").read_text(encoding="utf-8")
print("loadPostsTable body lines:", len(txt.splitlines()))
for l in txt.splitlines()[:50]:
    print(l)
