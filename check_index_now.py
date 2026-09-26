import os
from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
print("Exists:", index_path.exists(), "Size:", index_path.stat().st_size)

html = index_path.read_text(encoding="utf-8")
print("Has pane-pages:", 'id="pane-pages"' in html)
print("Has pane-groups:", 'id="pane-groups"' in html)
print("Has pane-posts:", 'id="pane-posts"' in html)
print("Has pane-tokens:", 'id="pane-tokens"' in html)
