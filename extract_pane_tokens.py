from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

pos_t = html.find('id="pane-tokens"')
pos_end_t = html.find('</section>', pos_t)
print("pane-tokens from", pos_t, "to", pos_end_t)
print(html[pos_t:pos_end_t+10])
