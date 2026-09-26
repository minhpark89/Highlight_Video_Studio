from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect pane-tokens
pos = html.find('id="pane-tokens"')
pos_end = html.find('</section>', pos)
print("=== pane-tokens ===")
print(html[pos:pos+2000])
