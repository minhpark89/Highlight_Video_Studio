import sys
sys.path.append(r'D:\News_Video_Studio')
from core.website_article_service import WebsiteArticleService, _BackendSession
import re

cfg_path = r'D:\Highlight_Video_Studio\config\website_config.json'
svc = WebsiteArticleService(cfg_path)
sess = _BackendSession(svc.cfg)
svc._ensure_session(sess)

# Let's inspect the create post page source on bestnews.cfx.bz
r = sess.http.get(svc.cfg.create_page_url)
print("Create page status:", r.status_code)

# Let's search for video in the entire create post HTML
for line in r.text.splitlines():
    if any(k in line.lower() for k in ['video', 'embed', 'youtube', 'player', 'iframe', 'source']):
        print("Line:", line.strip()[:150])
