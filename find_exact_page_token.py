import requests
import json
from pathlib import Path

base_dir = Path(r"D:\Highlight_Video_Studio")
tokens = json.loads((base_dir / "tokens_vault.json").read_text(encoding="utf-8"))
pages = json.loads((base_dir / "pages.json").read_text(encoding="utf-8"))

su_token = tokens[0]["token"]
p = pages[0]
pid = p["page_id"]

# Query /me/accounts from SU token to find this page's exact access_token
r = requests.get(f"https://graph.facebook.com/v22.0/me/accounts?limit=100&access_token={su_token}")
data = r.json().get("data", [])
print(f"Total accounts returned by SU token: {len(data)}")

page_token = None
for acc in data:
    if acc.get("id") == pid:
        page_token = acc.get("access_token")
        print(f"Found page {acc.get('name')} in me/accounts! Tasks:", acc.get("tasks"))
        break

if not page_token:
    print(f"Page {pid} not in first 25 of this SU token. Searching all SU tokens...")
    for idx, t in enumerate(tokens):
        st = t["token"]
        r2 = requests.get(f"https://graph.facebook.com/v22.0/me/accounts?limit=100&access_token={st}")
        for acc in r2.json().get("data", []):
            if acc.get("id") == pid:
                page_token = acc.get("access_token")
                print(f"Found in SU Token #{idx+1} ({t['name']})! Tasks: {acc.get('tasks')}")
                break
        if page_token: break

if page_token:
    print(f"Testing Reel publish with real Page Access Token: {page_token[:25]}...")
    import sys
    sys.path.insert(0, str(base_dir))
    from src.publisher.meta_reel_poster import MetaReelPoster
    poster = MetaReelPoster()
    video_file = base_dir / "output" / "job_1789889585_ca8470_clip_1.mp4"
    res = poster.publish_reel(
        page_id=pid,
        page_token=page_token,
        video_path=str(video_file),
        description="Test Reel upload via Meta Graph API #reels #viral",
        first_comment="🔥 Watch the full uncut footage here: https://bestnews.cfx.bz/article/test"
    )
    print("Publish Result:", json.dumps(res, indent=2, ensure_ascii=False))
else:
    print("Page not found in any SU token accounts.")
