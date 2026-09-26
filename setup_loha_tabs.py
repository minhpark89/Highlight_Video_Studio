# Build complete 4-tab LoHa Page layout script
import json
import re
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
INDEX_PATH = BASE_DIR / "web" / "templates" / "index.html"
APP_PATH = BASE_DIR / "web" / "app.py"

print("Checking index.html size:", INDEX_PATH.stat().st_size)
print("Checking app.py size:", APP_PATH.stat().st_size)
