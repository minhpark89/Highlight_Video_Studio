from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

pos_t = html.find('id="pane-tokens"')
pos_end_t = html.find('</section>', pos_t)

with open(r"D:\Highlight_Video_Studio\current_tokens_section.html", "w", encoding="utf-8") as f:
    f.write(html[pos_t:pos_end_t+10])

print("Saved current_tokens_section.html, len:", pos_end_t - pos_t)
