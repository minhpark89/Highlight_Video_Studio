from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
text = tmpl.read_text(encoding="utf-8")

pos = text.find("async function loadPostsTable()")
pos_end = text.find("tbody.innerHTML", pos)
print("loadPostsTable in templates/index.html:\n", text[pos:pos_end+30])
