from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's inspect where modal-token-group is in index.html
pos = html.find('id="modal-token-group"')
print("modal-token-group at:", pos)
if pos != -1:
    pos_end = html.find('<!-- /modal-token-group', pos)
    if pos_end == -1: pos_end = html.find('</div>\n    </div>\n  </div>', pos)
    print("modal snippet:")
    print(html[pos:pos+1500])
