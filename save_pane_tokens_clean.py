import re
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
html = (BASE_DIR / "web" / "templates" / "index.html").read_text(encoding="utf-8")

# Let's inspect pane-tokens in html
pos = html.find('id="pane-tokens"')
pos_end = html.find('</section>', pos)
print("pane-tokens length:", pos_end - pos)

with open(r"D:\Highlight_Video_Studio\pane_tokens_current_clean.html", "w", encoding="utf-8") as f:
    f.write(html[pos:pos_end+10])

print("Saved pane-tokens content successfully!")
