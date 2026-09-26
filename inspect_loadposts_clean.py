from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect where posts are rendered into rows
pos = html.find('async function loadPostsTable()')
pos_end = html.find('</script>', pos)
print("=== loadPostsTable CODE ===")
print(html[pos:pos+2500])
