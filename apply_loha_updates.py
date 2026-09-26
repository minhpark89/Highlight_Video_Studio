import os, json, re, shutil
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_FILE = BASE_DIR / "web" / "templates" / "index.html"
APP_FILE = BASE_DIR / "web" / "app.py"

print("Starting patch for Highlight_Video_Studio...")
