from pathlib import Path

html_tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
html_web = Path(r"D:\Highlight_Video_Studio\web\index.html").read_text(encoding="utf-8")

print("has 'post_fb_id' in tmpl?", "post_fb_id" in html_tmpl)
print("has 'post_fb_id' in web_idx?", "post_fb_id" in html_web)

pos = html_tmpl.find('async function loadPostsTable')
pos_end = html_tmpl.find('tbody.innerHTML', pos)
print("=== TEMPLATES loadPostsTable ===")
print(html_tmpl[pos:pos_end+30])
