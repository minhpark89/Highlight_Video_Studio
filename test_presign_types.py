import sys
sys.path.append(r'D:\News_Video_Studio')
from core.website_article_service import WebsiteArticleService, _BackendSession
import json

cfg_path = r'D:\Highlight_Video_Studio\config\website_config.json'
svc = WebsiteArticleService(cfg_path)
sess = _BackendSession(svc.cfg)
svc._ensure_session(sess)

print("Presign URL:", svc.cfg.presign_url)

# Let's test presign request with image vs video
try:
    r_img = sess.http.post(
        svc.cfg.presign_url,
        json={"extension": "jpg", "mime_type": "image/jpeg"},
        headers={"X-CSRF-TOKEN": sess.csrf_token}
    )
    print("Presign image test:", r_img.status_code, r_img.text[:300])
except Exception as e:
    print("Presign img err:", e)

try:
    r_vid = sess.http.post(
        svc.cfg.presign_url,
        json={"extension": "mp4", "mime_type": "video/mp4"},
        headers={"X-CSRF-TOKEN": sess.csrf_token}
    )
    print("Presign video test:", r_vid.status_code, r_vid.text[:300])
except Exception as e:
    print("Presign vid err:", e)
