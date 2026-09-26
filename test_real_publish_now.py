import sys
import json
import requests
from pathlib import Path

base_dir = Path(r"D:\Highlight_Video_Studio")
sys.path.insert(0, str(base_dir))
from src.publisher.meta_reel_poster import MetaReelPoster

tokens = json.loads((base_dir / "tokens_vault.json").read_text(encoding="utf-8"))
su_token = tokens[0]["token"]

# Get real page access token from /me/accounts
r = requests.get(f"https://graph.facebook.com/v22.0/me/accounts?limit=100&access_token={su_token}")
accs = r.json().get("data", [])
kevin = next((a for a in accs if a.get("id") == "1344682818724522"), None)
print("Kevin acc:", kevin.get("name"), "has page token?", bool(kevin.get("access_token")))

page_token = kevin["access_token"]
page_id = "1344682818724522"

poster = MetaReelPoster()
video_file = base_dir / "output" / "job_1789889585_ca8470_clip_1.mp4"

print("Publishing reel using Real Page Access Token...")
res = poster.publish_reel(
    page_id=page_id,
    page_token=page_token,
    video_path=str(video_file),
    description="Test Reel upload via Meta Graph API #reels #viral",
    first_comment="🔥 Full uncut footage: https://bestnews.cfx.bz/article/test"
)

print("Publish result:", json.dumps(res, indent=2, ensure_ascii=False))
