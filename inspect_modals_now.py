import os, json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# Let's inspect modal-publish-reel and modal-distribute-loha
for modal_id in ["modal-publish-reel", "modal-distribute-loha", "modal-add-group"]:
    pos = text.find(f'id="{modal_id}"')
    print(f"{modal_id} at pos: {pos}")
    if pos != -1:
        print(text[pos:pos+1200])
        print("="*40)
