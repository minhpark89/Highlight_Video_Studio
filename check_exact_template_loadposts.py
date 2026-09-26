from pathlib import Path

content = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")
print("Length:", len(content))

# Look for loadPostsTable
pos = content.find("async function loadPostsTable")
pos_end = content.find("</script>", pos)
print("loadPostsTable in templates/index.html:\n", content[pos:pos+2500])
