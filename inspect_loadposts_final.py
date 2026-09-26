from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect loadPostsTable in templates/index.html
pos = html.find('async function loadPostsTable()')
pos_end = html.find('</script>', pos)
print("=== loadPostsTable in templates/index.html ===")
print(html[pos:pos+2500])
