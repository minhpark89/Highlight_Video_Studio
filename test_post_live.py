import sys
from pathlib import Path
import json

base_dir = Path(r"D:\Highlight_Video_Studio")
sys.path.insert(0, str(base_dir))

from src.publisher.meta_reel_poster import MetaReelPoster

posts = json.loads((base_dir / "posts.json").read_text(encoding="utf-8"))
p = posts[0] # Let's test the due post
print("Testing post:", p["id"], p["page_name"], p["page_id"])
print("Token prefix:", (p.get("token") or "")[:20])
print("Video file:", p.get("clip_filename") or p.get("media_file"))

# Check if video exists
vpath = base_dir / "output" / (p.get("clip_filename") or p.get("media_file"))
print("Video exists?", vpath.exists())

poster = MetaReelPoster()
# Let's test checking page token with Graph API
import requests
token = p.get("token")
page_id = p.get("page_id")

try:
    r = requests.get(f"https://graph.facebook.com/v22.0/{page_id}?access_token={token}")
    print("Page check status:", r.status_code, r.text[:200])
except Exception as e:
    print("Graph API check error:", e)
