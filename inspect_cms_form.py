import sys
sys.path.append(r'D:\News_Video_Studio')
from core.website_article_service import WebsiteArticleService, _BackendSession
import re

cfg_path = r'D:\Highlight_Video_Studio\config\website_config.json'
svc = WebsiteArticleService(cfg_path)
sess = _BackendSession(svc.cfg)
svc._ensure_session(sess)

r = sess.http.get(svc.cfg.create_page_url)
print('Status:', r.status_code)
html = r.text

# Find form fields in create_page_url
form_inputs = re.findall(r'<input[^>]+name="([^"]+)"[^>]*>', html)
form_textareas = re.findall(r'<textarea[^>]+name="([^"]+)"[^>]*>', html)
print('Form inputs:', form_inputs)
print('Form textareas:', form_textareas)

# Let's inspect where description or content or video is in html
for line in html.splitlines():
    if any(k in line.lower() for k in ['video', 'media', 'presign', 'upload', 'tinymce', 'summernote', 'quill', 'editor']):
        print('Line:', line.strip()[:150])
