import os
import sys
from pathlib import Path

# Add paths
HVS_DIR = Path(r"D:\Highlight_Video_Studio")
NVS_DIR = Path(r"D:\News_Video_Studio")
sys.path.insert(0, str(HVS_DIR))
sys.path.insert(0, str(NVS_DIR))

from core.website_article_service import WebsiteArticleService, WebsiteConfig

cfg_path = HVS_DIR / "config" / "website_config.json"
svc = WebsiteArticleService(str(cfg_path))
print("CMS base_url:", svc.cfg.base_url)

# Test publish_article with body containing video tag
title = "Thrilling Sports Highlight Uncut Play 2026"
slug = "thrilling-sports-highlight-uncut-play-2026"
body_html = """
<div class="article-content">
  <p class="lead"><strong>Watch the complete uncut play and high-definition breakdown below:</strong></p>
  <div style="margin: 20px 0; text-align: center;">
    <video controls playsinline style="width: 100%; max-width: 720px; border-radius: 8px; background: #000;">
      <source src="https://bestnews.cfx.bz/storage/videos/sample.mp4" type="video/mp4">
      Your browser does not support HTML5 video streaming.
    </video>
  </div>
  <p>The thrilling moment captured here demonstrates incredible athletic precision and tactical execution under extreme pressure. Full analysis and commentary continue below.</p>
</div>
"""

res = svc.publish_article(
    title=title,
    slug=slug,
    body_html=body_html,
    dry_run=False
)
print("Live Publish Result:", res)
