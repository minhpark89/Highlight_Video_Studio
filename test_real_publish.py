import sys
from pathlib import Path
import json

base_dir = Path(r"D:\Highlight_Video_Studio")
sys.path.insert(0, str(base_dir))

from src.publisher.meta_reel_poster import MetaReelPoster

poster = MetaReelPoster()

# Load pages
pages = json.loads((base_dir / "pages.json").read_text(encoding="utf-8"))
p0 = pages[0]
page_id = p0["page_id"]
page_token = p0.get("access_token")
video_file = base_dir / "output" / "job_1789889585_ca8470_clip_1.mp4"

print(f"Testing real Reel publish to Page: {p0['page_name']} ({page_id})")
print(f"Token len: {len(page_token)}, Video exists: {video_file.exists()}")

res = poster.publish_reel(
    page_id=page_id,
    page_token=page_token,
    video_path=str(video_file),
    description="Test Reel upload via Meta Graph API #reels #viral",
    first_comment="🔥 Watch the full uncut footage here: https://bestnews.cfx.bz/article/test"
)

print("Publish result:", json.dumps(res, indent=2, ensure_ascii=False))
