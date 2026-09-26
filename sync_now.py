import shutil
from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
web_idx = Path(r"D:\Highlight_Video_Studio\web\index.html")

print("Templates:", tmpl.stat().st_size)
print("Web index:", web_idx.stat().st_size)

# Sync
shutil.copyfile(tmpl, web_idx)
print("Synced!")
