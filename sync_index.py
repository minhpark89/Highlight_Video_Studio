import shutil
from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
web_idx = Path(r"D:\Highlight_Video_Studio\web\index.html")

print("Templates index.html size:", tmpl.stat().st_size)
print("Web index.html size:", web_idx.stat().st_size)

# Sync templates/index.html to web/index.html just in case
shutil.copyfile(tmpl, web_idx)
print("Synced to web/index.html!")
