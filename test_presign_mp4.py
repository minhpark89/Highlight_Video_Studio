import sys
sys.path.append(r'D:\News_Video_Studio')
from core.website_article_service import WebsiteArticleService, _BackendSession
import json

cfg_path = r'D:\Highlight_Video_Studio\config\website_config.json'
svc = WebsiteArticleService(cfg_path)
sess = _BackendSession(svc.cfg)
svc._ensure_session(sess)

# Test presigned upload payload requirements
# Earlier we got: {"fileName":["The file name field is required."],"contentType":["The content type field is required."],"size":["The size field is required."]}
payload = {
    "fileName": "test_video.mp4",
    "contentType": "video/mp4",
    "size": 1024 * 1024 * 5 # 5MB
}
try:
    r = sess.http.post(svc.cfg.presign_url, json=payload, headers={"X-CSRF-TOKEN": sess.csrf_token})
    print("Presign mp4 status:", r.status_code)
    print("Presign mp4 text:", r.text[:300])
except Exception as e:
    print("Err:", e)
