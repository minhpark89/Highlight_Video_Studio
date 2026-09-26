import sys
import json
import requests
from pathlib import Path

base_dir = Path(r"D:\Highlight_Video_Studio")
sys.path.insert(0, str(base_dir))

from src.publisher.meta_reel_poster import MetaReelPoster

tokens = json.loads((base_dir / "tokens_vault.json").read_text(encoding="utf-8"))
pages = json.loads((base_dir / "pages.json").read_text(encoding="utf-8"))

# Let's find the real Page Access Token for Kevin Rogers (1344682818724522) from AutoPool 01
su_tok = tokens[0]["token"]
r = requests.get(f"https://graph.facebook.com/v22.0/me/accounts?limit=100&access_token={su_tok}")
accs = r.json().get("data", [])
kevin_acc = next((a for a in accs if a.get("id") == "1344682818724522"), None)

if kevin_acc:
    page_token = kevin_acc["access_token"]
    print(f"Found Kevin Rogers! Tasks: {kevin_acc.get('tasks')}")
    print(f"Page Access Token prefix: {page_token[:25]}... len: {len(page_token)}")
    
    # Check Meta documentation for Reels publishing:
    # 1. POST /{page-id}/video_reels with upload_phase=start
    # Let's test with MetaReelPoster
    poster = MetaReelPoster()
    video_path = base_dir / "output" / "job_1789889585_ca8470_clip_1.mp4"
    
    res = poster.publish_reel(
        page_id="1344682818724522",
        page_token=page_token,
        video_path=str(video_path),
        description="Testing Reel publish via Meta Graph API v22 #sports #reels",
        first_comment="🔥 Full match highlights: https://bestnews.cfx.bz/article/test"
    )
    print("Reel publish result:", json.dumps(res, indent=2, ensure_ascii=False))
else:
    print("Kevin Rogers not found in AutoPool 01 accounts")
