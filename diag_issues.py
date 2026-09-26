from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# 1. First, check why /api/posts/clear had Method Not Allowed / 500:
# In app.py, @app.route("/api/posts/clear", methods=["POST", "DELETE"])
# Let's fix app.py to also accept POST and DELETE, and ensure load_posts/save_posts are used properly.

# 2. Inspect layout gap for pane-settings and pane-website:
# Let's find why pane-website and pane-settings are shifted down.
# Check CSS for .pane
# Is there an empty container or flex pushing them down?
pos_ca = html.find('id="content-area"')
pos_sett = html.find('id="pane-settings"')
pos_web = html.find('id="pane-website"')
print(f"content-area at {pos_ca}, pane-settings at {pos_sett}, pane-website at {pos_web}")
