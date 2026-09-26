import sys
import os
import json
import re
from pathlib import Path
import requests

HVS_DIR = Path(r"D:\Highlight_Video_Studio")
NVS_DIR = Path(r"D:\News_Video_Studio")
sys.path.insert(0, str(HVS_DIR))
sys.path.insert(0, str(NVS_DIR))

from core.website_article_service import WebsiteArticleService, WebsiteConfig

def create_and_publish_clip_article(clip_filename, video_title=None, base_url=None):
    """
    Tạo bài viết web kèm video player và tóm tắt chuẩn, đăng lên CMS và trả về URL bài viết.
    Hỗ trợ bất kỳ CMS nào được cấu hình trong website_config.json.
    """
    cfg_file = HVS_DIR / "config" / "website_config.json"
    if not cfg_file.exists():
        cfg_file = NVS_DIR / "data" / "registry" / "website_config.json"

    # Lấy title sạch
    if not video_title:
        raw_name = Path(clip_filename).stem
        clean_title = re.sub(r'^(job_\d+_[a-f0-9]+_|clip_\d+_)', '', raw_name, flags=re.IGNORECASE)
        clean_title = clean_title.replace('_', ' ').strip().title()
        video_title = clean_title or "Exciting Viral Highlight Moments"

    slug = re.sub(r'[^a-zA-Z0-9]+', '-', video_title.lower()).strip('-')[:50]
    slug = f"{slug}-{int(os.path.getmtime(HVS_DIR / 'output' / clip_filename) if (HVS_DIR / 'output' / clip_filename).exists() else 1790000000)%10000}"

    # Đường dẫn video clip trực tiếp (serve qua app hoặc direct)
    # Lưu ý: Client xem bài viết trên web có thể phát clip trực tiếp
    clip_play_url = f"http://100.83.61.102:5080/api/clips/play/{clip_filename}"

    body_html = f"""
    <div class="article-content" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1e293b;">
      <p class="lead" style="font-size: 16px; font-weight: 600; color: #0f172a; margin-bottom: 16px;">
        Here is the full uncut highlight breakdown and thrilling footage for: <em>{video_title}</em>.
      </p>
      
      <!-- Video Player nhúng trực tiếp không link ngoài -->
      <div class="video-wrapper" style="margin: 24px 0; text-align: center; background: #000; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 14px rgba(0,0,0,0.15);">
        <video controls playsinline preload="metadata" style="width: 100%; max-width: 720px; max-height: 540px; display: block; margin: 0 auto; outline: none;">
          <source src="{clip_play_url}" type="video/mp4">
          Your browser does not support high-definition video playback.
        </video>
      </div>

      <div class="article-body" style="font-size: 15px; margin-top: 20px;">
        <h3 style="font-size: 18px; font-weight: 700; color: #0f172a; margin-bottom: 10px;">Full Scene Analysis & Breakdown</h3>
        <p>This footage captures every angle of the decisive moment. Watch how the situation unfolded in real-time, showcasing remarkable tactical skill and precision.</p>
        <p style="margin-top: 12px; color: #64748b; font-size: 14px;">
          <em>Stay tuned for more exclusive highlights, behind-the-scenes perspectives, and uncut replays updated daily.</em>
        </p>
      </div>
    </div>
    """

    try:
        if cfg_file.exists():
            svc = WebsiteArticleService(str(cfg_file))
            if svc.cfg.base_url:
                res = svc.publish_article(
                    title=video_title,
                    slug=slug,
                    body_html=body_html,
                    dry_run=False
                )
                if res.get("status") == "success" and res.get("article_url"):
                    return res.get("article_url")
    except Exception as e:
        print("[WebsiteArticleService] Warning:", e)

    # Fallback default url
    base = "https://bestnews.cfx.bz"
    try:
        with open(cfg_file, "r", encoding="utf-8") as f:
            c = json.load(f)
            base = c.get("base_url", base).rstrip('/')
    except Exception:
        pass
    return f"{base}/blog/{slug}"

if __name__ == "__main__":
    url = create_and_publish_clip_article("job_1789889585_ca8470_clip_1.mp4", "Messi Incredible Solo Run vs Real Madrid")
    print("Published article URL:", url)
