import sys
sys.path.append(r'D:\News_Video_Studio')
from core.website_article_service import WebsiteArticleService, _BackendSession
import json

cfg_path = r'D:\Highlight_Video_Studio\config\website_config.json'
svc = WebsiteArticleService(cfg_path)
sess = _BackendSession(svc.cfg)
svc._ensure_session(sess)

# Try uploading a small mp4 or dummy file via presigned upload or check presign url
print("Presign URL:", svc.cfg.presign_url)
print("Create post URL:", svc.cfg.create_post_url)

# Let's test svc.presign_upload if any
try:
    res = svc.presign_upload(r"D:\Highlight_Video_Studio\output\job_1789889585_ca8470_clip_1.mp4", dry_run=False)
    print("presign_upload video result:", res)
except Exception as e:
    print("presign_upload video err:", e)
