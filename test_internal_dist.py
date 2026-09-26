import traceback
from datetime import datetime, timedelta
import uuid
import re
import json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
OUTPUT_DIR = BASE_DIR / "output"

try:
    from core.page_manager import PageManager
    pm = PageManager(BASE_DIR)
    groups = pm.list_groups()
    print("Groups from pm:", len(groups))
    group = next((g for g in groups if g.get("id") == "group_bm1"), None)
    print("Found group:", group is not None)
    pages = pm.list_pages()
    print("Pages count:", len(pages))
    
    # check clips
    p_clips = list(OUTPUT_DIR.glob("*.mp4"))
    print("Clips in output:", len(p_clips))
except Exception as e:
    traceback.print_exc()
