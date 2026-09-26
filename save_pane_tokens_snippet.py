from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's inspect pane-tokens in html
pos = html.find('id="pane-tokens"')
pos_end = html.find('</section>', pos)
print("pane-tokens length:", pos_end - pos)

with open(r"D:\Highlight_Video_Studio\pane_tokens_snippet.txt", "w", encoding="utf-8") as out:
    out.write(html[pos:pos_end+10])

print("Wrote snippet, length:", pos_end - pos)
