import json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")

# Let's inspect page_groups.json
groups_file = BASE_DIR / "page_groups.json"
if groups_file.exists():
    print("page_groups.json:", groups_file.read_text(encoding="utf-8"))

# Let's inspect how groups are handled in app.py
with open(BASE_DIR / "web" / "app.py", "r", encoding="utf-8") as f:
    text = f.read()

for route in ['/api/groups', '/api/posts', '/api/distribute/batch', '/api/clips/purge_posted']:
    pos = text.find(f'"{route}"')
    if pos != -1:
        print(f"Route {route} found at {pos}")
