from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

# Let's inspect imports at the top
pos_import = text.find("from src.publisher.meta_reel_poster import MetaReelPoster")
print("Found MetaReelPoster at:", pos_import)
print(text[pos_import-50:pos_import+150])
