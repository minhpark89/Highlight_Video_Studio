import sys
from pathlib import Path
import json

base_dir = Path(r"D:\Highlight_Video_Studio")
sys.path.insert(0, str(base_dir))

from src.publisher.meta_reel_poster import MetaReelPoster

# Let's inspect meta_reel_poster.py implementation
poster = MetaReelPoster()
print("poster base_url:", poster.base_url)

# Test with 1 page and page access token
pages = json.loads((base_dir / "pages.json").read_text(encoding="utf-8"))
p0 = pages[0]
print("Page 0:", p0["page_name"], p0["page_id"])
print("Access token len:", len(p0.get("access_token", "")))

# Check sample video
vpath = base_dir / "output" / "job_1789889585_ca8470_clip_1.mp4"
print("Video exists?", vpath.exists(), "Size:", vpath.stat().st_size)
