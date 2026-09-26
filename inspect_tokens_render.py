from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's inspect renderTokens function or how tokens are rendered in pane-tokens
pos = html.find('function loadTokensOnly')
if pos == -1:
    pos = html.find('tokens-full-list-container')
print("Position:", pos)
if pos != -1:
    print(html[pos-100:pos+1500])
