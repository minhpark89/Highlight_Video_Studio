import sys
sys.path.append(r'D:\News_Video_Studio')
from core.website_article_service import WebsiteArticleService, _BackendSession
import json

cfg_path = r'D:\Highlight_Video_Studio\config\website_config.json'
svc = WebsiteArticleService(cfg_path)
sess = _BackendSession(svc.cfg)
svc._ensure_session(sess)

# Let's inspect /admin/dashboard or /backend/posts to see what endpoints exist for uploading media or creating posts
# Let's check routes in the frontend JavaScript on /backend/posts
r = sess.http.get(f"{svc.cfg.base_url}/backend/posts?create=1")
print("Status:", r.status_code)
# Search for upload endpoints or api routes in JS
import re
urls = set(re.findall(r'[\'"]([^\'"]*(?:upload|media|video|post)[^\'"]*)[\'"]', r.text, re.IGNORECASE))
for u in sorted(urls):
    if any(k in u.lower() for k in ['upload', 'media', 'video', 'api']):
        print("Found URL/Key:", u)
