from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's inspect pane-tokens in detail
pos_t = html.find('id="pane-tokens"')
pos_t_end = html.find('</section>', pos_t)
print("pane-tokens length:", pos_t_end - pos_t)
print(html[pos_t:pos_t_end])
