from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's see what loadTokensOnly looks like
pos = html.find('async function loadTokensOnly()')
pos_end = html.find('</script>', pos)
print(html[pos:pos+1600])
