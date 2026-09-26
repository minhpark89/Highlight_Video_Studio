from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
pos = tmpl.find("async function loadPostsTable")
pos_end = tmpl.find("tbody.innerHTML", pos)
print("=== TEMPLATES loadPostsTable ===")
print(tmpl[pos:pos_end+50])

web = Path(r"D:\Highlight_Video_Studio\web\index.html").read_text(encoding="utf-8")
pos_w = web.find("async function loadPostsTable")
pos_end_w = web.find("tbody.innerHTML", pos_w)
print("\n=== WEB INDEX loadPostsTable ===")
print(web[pos_w:pos_end_w+50])
