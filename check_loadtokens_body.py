from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's inspect loadTokensOnly function in index.html
pos = html.find('async function loadTokensOnly')
if pos != -1:
    pos_end = html.find('</script>', pos)
    print("loadTokensOnly code snippet:")
    print(html[pos:pos+1200])
