import sys
sys.path.insert(0, r"D:\Highlight_Video_Studio")
from web.app import app

print("app.template_folder:", app.template_folder)
print("app.root_path:", app.root_path)

import jinja2
env = app.jinja_env
template_source, filename, uptodate = env.loader.get_source(env, "index.html")
print("Template filename being loaded by Flask:", filename)
print("Has 'Xem Reel Facebook' in template source?", "Xem Reel Facebook" in template_source)
print("Has 'pages-per-token-input' in template source?", "pages-per-token-input" in template_source)
