import shutil
from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
web_idx = Path(r"D:\Highlight_Video_Studio\web\index.html")

shutil.copyfile(tmpl, web_idx)
print("Synced templates to web/index.html:", tmpl.stat().st_size, web_idx.stat().st_size)
