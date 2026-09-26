import sys
from pathlib import Path

# Add D:\Highlight_Video_Studio to sys.path
sys.path.insert(0, r"D:\Highlight_Video_Studio")

from core.page_manager import PageManager
pm = PageManager(Path(r"D:\Highlight_Video_Studio"))
print("PageManager loaded successfully!")
print("Groups count:", len(pm.list_groups()))
print("Pages count:", len(pm.list_pages()))
