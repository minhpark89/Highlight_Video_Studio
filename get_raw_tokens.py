from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
INDEX_PATH = BASE_DIR / "web" / "templates" / "index.html"
html = INDEX_PATH.read_text(encoding="utf-8")

pos_t = html.find('id="pane-tokens"')
pos_end_t = html.find('</section>', pos_t)

print("Found pane-tokens at", pos_t, "to", pos_end_t)
with open(r"D:\Highlight_Video_Studio\pane_tokens_raw.txt", "w", encoding="utf-8") as f:
    f.write(html[pos_t:pos_end_t+10])

print("Wrote pane_tokens_raw.txt")
