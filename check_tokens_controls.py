from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect pane-tokens around loha-token-threads and loha-posts-per-page
pos = html.find('id="loha-token-threads"')
print(html[pos-200:pos+1200])
