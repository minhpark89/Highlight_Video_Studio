from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's see what loadTokensOnly does
pos = html.find('async function loadTokensOnly')
print("pos:", pos)
if pos != -1:
    print(html[pos:pos+1500])
