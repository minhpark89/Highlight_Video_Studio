import os
import sys
import json
import re
import html
try:
    import cv2
    HAS_CV2 = True
except Exception:
    HAS_CV2 = False
import subprocess
import logging
from pathlib import Path
import requests

logger = logging.getLogger("website_publisher")

HVS_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(HVS_DIR))

try:
    from core.website_article_service import WebsiteArticleService, WebsiteServiceError, _BackendSession
    HAS_WEBSITE_SVC = True
except Exception as exc:
    WebsiteServiceError = RuntimeError
    logger.error("WebsiteArticleService import failed: %s", exc)
    HAS_WEBSITE_SVC = False

def get_website_config():
    """Lấy config CMS website được lưu cục bộ trong HVS."""
    cfg_file = HVS_DIR / "config" / "website_config.json"
    if cfg_file.exists():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                return json.load(f), cfg_file
        except Exception:
            pass
    return {"base_url": "https://bestnews.cfx.bz", "username": "admin", "password": ""}, cfg_file

def get_llm_config():
    """Lấy cấu hình LLM từ config.json."""
    try:
        with open(HVS_DIR / "config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
            return cfg.get("llm", {})
    except Exception:
        return {"api_base": "", "api_key": "", "model": "", "task_models": {}}

def get_task_model(task: str, llm_cfg: dict = None) -> str:
    """Return a task-specific model, falling back to the verified main model."""
    cfg = llm_cfg or get_llm_config()
    task_models = cfg.get("task_models") if isinstance(cfg.get("task_models"), dict) else {}
    return str(task_models.get(task) or cfg.get("model") or "").strip()


def get_image_provider_config(model_override: str = "") -> dict:
    """Resolve the dedicated image provider, with legacy LLM image settings as fallback."""
    try:
        with open(HVS_DIR / "config.json", "r", encoding="utf-8") as f:
            root_cfg = json.load(f)
    except Exception:
        root_cfg = {}
    image_cfg = root_cfg.get("image_provider") if isinstance(root_cfg.get("image_provider"), dict) else {}
    llm_cfg = root_cfg.get("llm") if isinstance(root_cfg.get("llm"), dict) else {}
    return {
        "api_base": str(image_cfg.get("api_base") or llm_cfg.get("api_base") or "").strip(),
        "api_key": str(image_cfg.get("api_key") or llm_cfg.get("api_key") or "").strip(),
        "model": str(model_override or image_cfg.get("model") or get_task_model("image", llm_cfg) or "").strip(),
    }

def _llm_headers(api_key: str) -> dict:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if api_key:
        headers.update({"Authorization": f"Bearer {api_key}", "x-api-key": api_key, "api-key": api_key})
    return headers

def get_clip_metadata(clip_filename: str) -> dict:
    """
    Tìm thông tin video gốc từ jobs.json hoặc crawled_videos.json.
    Tuyệt đối loại bỏ triệt để mọi chữ 'Clip 1', 'Clip 2', 'job_...', 'Video Highlight'.
    """
    jobs_file = HVS_DIR / "jobs.json"
    crawled_file = HVS_DIR / "crawled_videos.json"

    meta = {
        "clip_filename": clip_filename,
        "clean_title": "",
        "video_title": "",
        "youtube_url": "",
        "job_id": "",
        "description": "",
        "youtube_id": "",
        "long_video_path": ""
    }

    # 1. Tìm trong jobs.json
    matched_job = None
    if jobs_file.exists():
        try:
            with open(jobs_file, "r", encoding="utf-8", errors="ignore") as f:
                jobs = json.load(f)
                for j in jobs:
                    for c in j.get("clips", []):
                        if c.get("filename") == clip_filename:
                            matched_job = j
                            meta["job_id"] = j.get("id") or ""
                            meta["youtube_url"] = j.get("youtube_url") or ""
                            vt = (j.get("video_title") or "").strip()
                            if vt and not re.search(r'^(video highlight|job_\d+|clip_\d+)', vt, re.IGNORECASE):
                                meta["video_title"] = vt
                            break
                    if matched_job:
                        break
        except Exception:
            pass

    # 2. Tìm youtube_id
    y_url = meta.get("youtube_url", "")
    if "v=" in y_url:
        meta["youtube_id"] = y_url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in y_url:
        meta["youtube_id"] = y_url.split("youtu.be/")[1].split("?")[0]

    # Kiểm tra file video gốc dài trong downloads/
    if meta.get("job_id"):
        long_path = HVS_DIR / "downloads" / f"{meta['job_id']}.mp4"
        if long_path.exists():
            meta["long_video_path"] = str(long_path)

    # 3. Tìm ngược sang crawled_videos.json để lấy title video thật
    if (not meta["video_title"] or len(meta["video_title"]) < 10) and crawled_file.exists():
        try:
            with open(crawled_file, "r", encoding="utf-8", errors="ignore") as f:
                crawled = json.load(f)
                for cv in crawled:
                    if (y_url and cv.get("url") == y_url) or (meta["youtube_id"] and cv.get("id") == meta["youtube_id"]):
                        meta["video_title"] = cv.get("title") or meta["video_title"]
                        meta["description"] = cv.get("description") or ""
                        break
        except Exception:
            pass

    # 4. Lọc sạch triệt để: KHÔNG BAO GIỜ ĐỂ CHỮ "Clip 1", "Clip 2", "job_..."
    v_clean = meta["video_title"]
    v_clean = re.sub(r'^(Video Highlight|job_\d+_[a-f0-9]+|clip[_\s\-]*\d+)\s*', '', v_clean, flags=re.IGNORECASE).strip()
    
    # Nếu vẫn bị trống hoặc còn là mã rác (VD: "Clip 2", "job_...") -> Đặt tiêu đề giật gân tự nhiên
    if not v_clean or len(v_clean) < 8 or re.match(r'^(clip|job|highlight)', v_clean, re.IGNORECASE):
        v_clean = "Shocking High-Stakes Encounter & Dramatic Revelation"

    meta["video_title"] = v_clean.title()
    meta["clean_title"] = meta["video_title"]

    return meta

def generate_llm_hook_image(video_title: str, model_override: str = "") -> str:
    """
    Sinh ảnh HOOK THUMBNAIL bằng AI Gemini (gemini-3.1-flash-image)
    chuẩn 100% phong cách giật gân, tò mò tột đỉnh như hình mẫu boss gửi:
    - Text 3D ĐỎ RỰC viền TRẮNG cực dày và to ở nửa trên: 'WILDEST TAKEDOWNS!' hoặc 'SHOCKING REVELATION!'
    - Banner vàng chữ đen: "You Won't Believe This"
    - Vòng tròn đỏ neon khoanh chi tiết kịch tính
    - Mũi tên đỏ chỉ thẳng vào vòng tròn
    - Biểu tượng camera '● REC BODYCAM' góc trái
    - 16:9 widescreen, cinematic, cực nét!
    """
    import base64
    image_cfg = get_image_provider_config(model_override)
    api_base = image_cfg["api_base"]
    api_key = image_cfg["api_key"]
    model = image_cfg["model"]
    if model == "__video_frame__" or not api_base or not model:
        logger.info("Use video frame fallback for article hook image")
        return ""

    prompt = f"""A viral YouTube thumbnail and article hook image for a dramatic video: "{video_title}".
Exact required visual elements matching viral clickbait standard:
1. Scene: High-stakes, intense cinematic night police bodycam or dramatic street confrontation. Rain on asphalt with glowing emergency red and blue police cruiser strobe lights in background.
2. In the top half, MASSIVE 3D bold sensational text in thick condensed uppercase red font with heavy white stroke outline: 'WILDEST TAKEDOWNS!'
3. Directly beneath the red text, a bright yellow rectangular badge with bold black text: "You Won't Believe This".
4. A bright glowing neon red circular outline highlighting the critical focal action on the ground.
5. A bold curved red 3D arrow pointing directly at the glowing red circle.
6. In top-left corner, a sleek camera viewfinder overlay icon: '● REC BODYCAM' with white corner brackets.
7. Ultra-high resolution, photorealistic, cinematic lighting, 16:9 widescreen format."""

    headers = _llm_headers(api_key)
    temp_dir = HVS_DIR / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    out_file = str(temp_dir / f"llm_hook_{abs(hash(video_title)) % 100000}.jpg")

    def save_image_value(value) -> str:
        if not value:
            return ""
        if isinstance(value, dict):
            value = value.get("url") or value.get("b64_json")
        value = str(value)
        try:
            if value.startswith("http://") or value.startswith("https://"):
                downloaded = requests.get(value, timeout=90)
                downloaded.raise_for_status()
                Path(out_file).write_bytes(downloaded.content)
            else:
                raw_b64 = value.split("base64,", 1)[1] if "base64," in value else value
                Path(out_file).write_bytes(base64.b64decode(raw_b64))
            logger.info("Generated image-provider Hook Image: %s", out_file)
            return out_file
        except Exception as exc:
            logger.warning("Cannot save generated image response: %s", exc)
            return ""

    attempts = [
        (f"{api_base.rstrip('/')}/images/generations", {
            "model": model, "prompt": prompt, "n": 1, "size": "1536x1024"
        }),
        (f"{api_base.rstrip('/')}/chat/completions", {
            "model": model, "messages": [{"role": "user", "content": prompt}]
        }),
    ]
    for url, payload in attempts:
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            if resp.status_code != 200:
                logger.warning("Image provider %s returned HTTP %s", url, resp.status_code)
                continue
            res_json = resp.json()
            data = res_json.get("data") or []
            if data and isinstance(data[0], dict):
                saved = save_image_value(data[0].get("b64_json") or data[0].get("url"))
                if saved:
                    return saved
            choices = res_json.get("choices") or []
            message = choices[0].get("message", {}) if choices and isinstance(choices[0], dict) else {}
            images = message.get("images") or []
            if images:
                saved = save_image_value(images[0].get("image_url") if isinstance(images[0], dict) else images[0])
                if saved:
                    return saved
        except Exception as exc:
            logger.warning("Image provider request failed at %s: %s", url, exc)

    return ""

def upload_long_video_to_public_stream(meta: dict, clip_filename: str) -> str:
    """
    TẬP TRUNG 100% PHÁT QUA DIRECT HTML5 VIDEO PLAYER (BẢN FULL DÀI):
    Upload file MP4 gốc dài (downloads/*.mp4) lên VPS public hosting Caddy (https://studio.shopkitai.com/videos/...).
    Hỗ trợ phát trực tiếp trên iPhone, Android, PC mượt mà 100%, có Range requests, tua được!
    """
    long_path = meta.get("long_video_path")
    target_video_file = None
    target_stream_name = None

    if long_path and os.path.exists(long_path):
        target_video_file = Path(long_path)
        target_stream_name = target_video_file.name
    else:
        clip_path = HVS_DIR / "output" / clip_filename
        if clip_path.exists():
            target_video_file = clip_path
            target_stream_name = clip_filename

    if not target_video_file or not target_video_file.exists():
        return ""

    cfg_data, cfg_file = get_website_config()
    if not HAS_WEBSITE_SVC:
        raise WebsiteServiceError("Bản cài thiếu WebsiteArticleService")
    if not cfg_file.exists():
        raise WebsiteServiceError("Chưa cấu hình Website CMS")

    svc = WebsiteArticleService(str(cfg_file))
    # CMS cấp presigned HTTPS URL và public URL. Cách này chạy trên mọi máy,
    # không phụ thuộc SSH key hoặc username Windows của máy build.
    public_url = svc.upload_video(str(target_video_file))
    svc.verify_public_media(public_url, require_range=True)
    return public_url

def extract_and_upload_article_assets(clip_filename: str, video_title: str) -> tuple:
    """
    1. Tạo ảnh Hook bằng AI Gemini (gemini-3.1-flash-image) chuẩn hình mẫu boss gửi.
    2. Upload ảnh Hook lên CDN để làm Thumbnail đầu trang (og:image / first comment).
    3. Trích xuất 2 frame từ video làm ảnh minh họa diễn biến trong bài.
    """
    cfg_data, cfg_file = get_website_config()
    sess = None
    svc = None
    if HAS_WEBSITE_SVC and cfg_file.exists():
        svc = WebsiteArticleService(str(cfg_file))
        sess = _BackendSession(svc.cfg)
        svc._ensure_session(sess)

    # 1. Sinh ảnh Hook LLM
    hook_img_local = generate_llm_hook_image(video_title)
    hero_cdn_url = ""

    if hook_img_local and os.path.exists(hook_img_local) and sess:
        try:
            hero_cdn_url = svc._presign_and_upload(sess, hook_img_local)
            logger.info(f"Uploaded LLM Hook image to CDN: {hero_cdn_url}")
        except Exception as _e_hook:
            logger.warning(f"Failed to upload LLM Hook image to CDN: {_e_hook}")

    # 2. Trích xuất ảnh minh họa từ video
    body_imgs_cdn = []
    video_path = HVS_DIR / "output" / clip_filename
    if not video_path.exists():
        video_path = HVS_DIR / "downloads" / clip_filename

    if video_path.exists() and sess:
        try:
            if HAS_CV2:
                cap = cv2.VideoCapture(str(video_path))
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if total_frames > 10:
                    for idx, pct in enumerate([0.40, 0.80]):
                        cap.set(cv2.CAP_PROP_POS_FRAMES, int(total_frames * pct))
                        ret, frame = cap.read()
                        if ret:
                            fpath = HVS_DIR / "temp" / f"body_frame_{Path(clip_filename).stem}_{idx}.jpg"
                            cv2.imwrite(str(fpath), frame)
                            try:
                                cdn_link = svc._presign_and_upload(sess, str(fpath))
                                body_imgs_cdn.append(cdn_link)
                            except Exception:
                                pass
                cap.release()
            else:
                ffmpeg_bin = str(HVS_DIR / "bin" / "ffmpeg.exe")
                if not os.path.exists(ffmpeg_bin):
                    ffmpeg_bin = "ffmpeg"
                for idx, ss in enumerate(["00:00:03", "00:00:08"]):
                    fpath = HVS_DIR / "temp" / f"body_frame_{Path(clip_filename).stem}_{idx}.jpg"
                    fpath.parent.mkdir(parents=True, exist_ok=True)
                    subprocess.run([ffmpeg_bin, "-y", "-ss", ss, "-i", str(video_path), "-vframes", "1", "-q:v", "2", str(fpath)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if fpath.exists():
                        try:
                            cdn_link = svc._presign_and_upload(sess, str(fpath))
                            body_imgs_cdn.append(cdn_link)
                        except Exception:
                            pass
        except Exception as e:
            logger.warning(f"Error extracting body frames: {e}")

    # Fallback nếu LLM hook lỗi thì lấy frame đầu
    if not hero_cdn_url and body_imgs_cdn:
        hero_cdn_url = body_imgs_cdn[0]

    return hero_cdn_url, body_imgs_cdn

def generate_deep_article_content(video_title: str, hero_img: str, body_imgs: list, video_stream_url: str) -> tuple:
    """
    Sinh bài viết dài chuyên sâu 500+ từ chuẩn báo chí quốc tế:
    - ĐẦU BÀI: Hiển thị ngay tấm ảnh Hook LLM to sắc nét (Hero Banner)!
    - Mở đầu lôi cuốn
    - 2 phần phân tích chuyên sâu + ảnh minh họa diễn biến
    - CUỐI BÀI: Video Player HTML5 phát file video MP4 gốc dài (100% chạy trên điện thoại và máy tính)!
    """
    if not video_stream_url or not str(video_stream_url).startswith("https://"):
        raise WebsiteServiceError("Video chưa có HTTPS public URL hợp lệ")
    title = video_title or "Uncut Breakdown & Critical Scene Analysis"
    
    # 1. Khối ảnh Hero Hook nằm ngay đầu bài viết (dưới tiêu đề)
    hero_top_html = ""
    if hero_img:
        hero_top_html = f"""
        <div class="article-hero-banner" style="margin: 0 0 28px 0; text-align: center;">
          <img src="{hero_img}" alt="{title} official hook" style="width: 100%; max-width: 820px; border-radius: 12px; box-shadow: 0 6px 22px rgba(0,0,0,0.18); display: block; margin: 0 auto;">
        </div>
        """

    img_mid_html = ""
    if body_imgs and len(body_imgs) > 0:
        img_mid_html = f"""
        <div style="margin: 24px 0; text-align: center;">
          <img src="{body_imgs[0]}" alt="{title} tactical sequence" style="width: 100%; max-width: 720px; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.12);">
          <p style="font-size: 13px; color: #64748b; margin-top: 6px; font-style: italic;">Detailed frame capture showing tactical movement and the pivotal turning point.</p>
        </div>
        """
    
    img_late_html = ""
    if body_imgs and len(body_imgs) > 1:
        img_late_html = f"""
        <div style="margin: 24px 0; text-align: center;">
          <img src="{body_imgs[1]}" alt="{title} dramatic climax" style="width: 100%; max-width: 720px; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.12);">
          <p style="font-size: 13px; color: #64748b; margin-top: 6px; font-style: italic;">The decisive climax captured seconds before the conclusion.</p>
        </div>
        """

    llm_cfg = get_llm_config()
    api_base = str(llm_cfg.get("api_base") or "").strip()
    api_key = str(llm_cfg.get("api_key") or "").strip()
    model = get_task_model("article", llm_cfg)

    prompt = f"""You are a senior sports and viral investigative journalist writing an in-depth article for a global media publication.
Write an authentic, context-rich article in English for the topic: "{title}".
Requirements:
1. "lead_paragraph": A dramatic 3-sentence introduction detailing the high stakes, tension, and what stunned the spectators.
2. "section_1_title": "The Decisive Breakdown: What Truly Unfolded"
3. "section_1_content": 2 rich paragraphs breaking down the technical precision, the immediate reaction, and why conventional wisdom failed.
4. "section_2_title": "Inside the Climax: Tactical Genius & Aftermath"
5. "section_2_content": 2 paragraphs exploring the aftermath, expert opinions, and the lasting significance of this scene.
6. Make it thorough, journalistic, and captivating (approx 450-600 words).
Output strictly valid JSON only:
{{
  "seo_title": "{title} - Full Uncut Breakdown & Scene Analysis",
  "lead_paragraph": "...",
  "section_1_title": "...",
  "section_1_content": "...",
  "section_2_title": "...",
  "section_2_content": "..."
}}"""

    seo_title = f"{title} - Full Uncut Breakdown & Scene Analysis"
    lead = f"Moments of sheer brilliance and unexpected drama rarely happen in isolation. In '{title}', viewers witnessed a breathtaking sequence of events that pushed athletic instincts and split-second decision-making to the absolute limit."
    s1_title = "The Decisive Sequence: Unraveling the Crucial Seconds"
    s1_content = "From the opening moments of this encounter, the tactical momentum shifted with dizzying speed. Observers initially anticipated a routine play, yet minute adjustments in spacing and pressure created an unanticipated opening that changed everything."
    s2_title = "Aftermath & Tactical Takeaways"
    s2_content = "Replaying the sequence frame-by-frame reveals subtleties that casual viewers easily missed in real-time. The coordination and the raw technical mastery displayed under extreme duress offer a masterclass in modern execution."

    try:
        if not api_base or not model:
            raise ValueError("Chưa cấu hình endpoint/model viết bài")
        url = f"{api_base.rstrip('/')}/chat/completions"
        headers = _llm_headers(api_key)
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You write structured, thorough journalistic feature articles. Respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1800,
            "temperature": 0.7
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            c = resp.json()["choices"][0]["message"]["content"].strip()
            c = re.sub(r"^```json\s*", "", c)
            c = re.sub(r"\s*```$", "", c)
            d = json.loads(c, strict=False)
            seo_title = d.get("seo_title") or seo_title
            lead = d.get("lead_paragraph") or lead
            s1_title = d.get("section_1_title") or s1_title
            s1_content = d.get("section_1_content") or s1_content
            s2_title = d.get("section_2_title") or s2_title
            s2_content = d.get("section_2_content") or s2_content
    except Exception as exc:
        logger.warning(f"LLM deep article generation failed: {exc}")

    safe_title = html.escape(str(title))
    safe_lead = html.escape(str(lead))
    safe_s1_title = html.escape(str(s1_title))
    safe_s1_content = html.escape(str(s1_content)).replace(chr(10), '<br><br>')
    safe_s2_title = html.escape(str(s2_title))
    safe_s2_content = html.escape(str(s2_content)).replace(chr(10), '<br><br>')
    body_html = f"""
    <div class="article-content" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.8; color: #1e293b; max-width: 820px; margin: 0 auto; font-size: 16px;">
      
      {hero_top_html}

      <p class="lead" style="font-size: 18px; font-weight: 600; color: #0f172a; line-height: 1.7; margin-bottom: 24px; border-left: 4px solid #38bdf8; padding-left: 16px; background: rgba(56, 189, 248, 0.04); padding-top: 10px; padding-bottom: 10px; border-radius: 0 8px 8px 0;">
        {safe_lead}
      </p>

      <div class="article-body-section" style="margin-bottom: 24px;">
        <h2 style="font-size: 21px; font-weight: 800; color: #0f172a; margin-top: 28px; margin-bottom: 14px;">
          {safe_s1_title}
        </h2>
        <p style="margin-bottom: 16px;">
          {safe_s1_content}
        </p>
      </div>

      {img_mid_html}

      <div class="article-body-section" style="margin-bottom: 28px;">
        <h2 style="font-size: 21px; font-weight: 800; color: #0f172a; margin-top: 28px; margin-bottom: 14px;">
          {safe_s2_title}
        </h2>
        <p style="margin-bottom: 16px;">
          {safe_s2_content}
        </p>
      </div>

      {img_late_html}

      <!-- KHỐI XEM FULL VIDEO GỐC DÀI NẰM DƯỚI ĐÁY BÀI VIẾT (DIRECT HTML5 STREAMING 100% PHÁT MƯỢT) -->
      <div class="full-video-section" style="margin-top: 36px; padding: 24px; background: #0b1120; border-radius: 14px; border: 1px solid #1e293b; box-shadow: 0 8px 28px rgba(0,0,0,0.25); text-align: center;">
        <div style="display: inline-flex; align-items: center; gap: 8px; background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 6px 14px; border-radius: 999px; font-size: 12.5px; font-weight: 800; text-transform: uppercase; margin-bottom: 12px; border: 1px solid rgba(56, 189, 248, 0.3);">
          <i class="bi bi-play-circle-fill"></i> Full Uncut Footage
        </div>
        <h3 style="font-size: 20px; font-weight: 800; color: #f8fafc; margin-top: 4px; margin-bottom: 16px;">
          Watch The Complete Full-Length Uncut Video Below
        </h3>
        <p style="font-size: 14px; color: #94a3b8; max-width: 600px; margin: 0 auto 20px auto;">
          Experience every unedited angle and decisive moment from start to finish. Stream the complete footage below in full high definition.
        </p>
        
        <div style="margin: 0 auto; max-width: 760px; border-radius: 12px; overflow: hidden; background: #000; box-shadow: 0 4px 20px rgba(0,0,0,0.5);">
          <video controls playsinline preload="metadata" poster="{hero_img}" style="width: 100%; max-height: 520px; display: block; outline: none;">
            <source src="{video_stream_url}" type="video/mp4">
            Trình duyệt của bạn không hỗ trợ phát video trực tiếp.
          </video>
        </div>
        
        <div style="font-size: 12px; color: #64748b; margin-top: 14px;">
          Official Broadcast Stream • 1080p HD • All Rights Reserved
        </div>
      </div>

    </div>
    """

    return seo_title, body_html

def generate_curiosity_comment_with_llm(video_title: str, article_url: str, enable_llm: bool = True) -> str:
    """
    Sinh First Comment gây tò mò (Curiosity Gap) bằng AI LLM (Gemini-3-Flash) dẫn link web.
    Fallback về mẫu chuẩn cố định nếu tắt LLM hoặc lỗi mạng.
    """
    fallback_comment = (
        f"🔥 Watch the full uncut footage and breakdown here: {article_url}\n"
        f"👉 Scroll down the article to stream the complete high-definition video!"
    )

    if not enable_llm:
        return fallback_comment

    llm_cfg = get_llm_config()
    api_base = str(llm_cfg.get("api_base") or "").strip()
    api_key = str(llm_cfg.get("api_key") or "").strip()
    model = get_task_model("first_comment", llm_cfg)

    prompt = f"""You are a master social media growth marketer. Write ONE viral, high-CTR First Comment in English for a Facebook Reel titled: "{video_title}".
Rules:
1. Create an intense Curiosity Gap hook about the full uncut scene, key revelation, or dramatic turnaround.
2. Must naturally incorporate this exact article link: {article_url}
3. End with a clear call-to-action to scroll down the article page to stream the full video player.
4. Keep it under 260 characters total, use 2-3 engaging emojis.
5. Return ONLY the comment text. No commentary, no quotation marks."""

    try:
        if not api_base or not model:
            raise ValueError("Chưa cấu hình endpoint/model First Comment")
        url = f"{api_base.rstrip('/')}/chat/completions"
        headers = _llm_headers(api_key)
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You write viral, curiosity-piquing first comments in English. Return only the final comment text."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 120,
            "temperature": 0.8
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=45)
        if resp.status_code == 200:
            res_json = resp.json()
            comment = res_json["choices"][0]["message"]["content"].strip()
            if comment.startswith('"') and comment.endswith('"'):
                comment = comment[1:-1].strip()
            if article_url not in comment:
                comment += f"\n👉 Full uncut video: {article_url}"
            # Facebook accepts longer comments, but keeping this compact gives
            # the requested high-CTR first-comment format.
            if len(comment) > 500:
                comment = comment[:500].rsplit(" ", 1)[0]
                if article_url not in comment:
                    comment = f"🔥 Full uncut story and video: {article_url}"
            return comment
        else:
            logger.warning(f"LLM comment gen error: {resp.status_code} {resp.text}")
    except Exception as exc:
        logger.warning(f"LLM comment gen exception (using fallback): {exc}")

    return fallback_comment

def publish_clip_to_website_cms(clip_filename: str, video_title: str = None) -> tuple:
    """
    Tự động:
    1. Đưa VIDEO GỐC DÀI (Full video gốc) lên stream công khai VPS Caddy (100% phát mượt mà, tua được)
    2. Tạo ảnh HOOK AI bằng LLM (gemini-3.1-flash-image) chuẩn hình mẫu boss gửi (chữ 3D đỏ to, banner vàng, vòng tròn đỏ, icon REC) và upload CDN
    3. ĐẶT ẢNH HOOK NGAY ĐẦU BÀI VIẾT và làm Thumbnail đại diện bài viết (og:image)
    4. Viết bài chuyên sâu 500+ từ, đặt Video Player Full ở cuối bài
    5. Đăng bài lên CMS với slug & title 100% sạch, KHÔNG BAO GIỜ dính chữ "Clip 1", "Clip 2" hay mã job.
    Trả về: (article_url, hero_image_url)
    """
    cfg_data, cfg_file = get_website_config()
    if not HAS_WEBSITE_SVC:
        raise WebsiteServiceError("Bản cài thiếu WebsiteArticleService")
    if not cfg_file.exists():
        raise WebsiteServiceError("Chưa cấu hình Website CMS")
    base_url = cfg_data.get("base_url", "https://bestnews.cfx.bz").rstrip("/")

    # 1. Metadata chuẩn sạch, loại bỏ hoàn toàn 'Clip 1', 'Clip 2'
    meta = get_clip_metadata(clip_filename)
    if not video_title or re.search(r'^(video highlight|job_\d+|clip_\d+)', video_title, re.IGNORECASE):
        video_title = meta.get("video_title") or meta.get("clean_title")

    # 2. Upload/Stream VIDEO GỐC DÀI qua direct HTML5 video player (100% chạy trên mọi thiết bị)
    video_stream_url = upload_long_video_to_public_stream(meta, clip_filename)
    if not video_stream_url:
        raise WebsiteServiceError("Upload video không trả public URL")

    # 3. Tạo ảnh HOOK AI bằng LLM & Trích xuất ảnh minh họa
    hero_img, body_imgs = extract_and_upload_article_assets(clip_filename, video_title)

    # 4. Sinh bài viết chi tiết, có ảnh Hook ngay đầu bài và Video Player Full ở CUỐI bài
    seo_title, body_html = generate_deep_article_content(video_title, hero_img, body_imgs, video_stream_url)

    # 5. Tạo slug duy nhất và sạch sẽ (không chứa chữ clip-2 hay job_)
    clean_slug = re.sub(r'[^a-zA-Z0-9]+', '-', video_title.lower()).strip('-')[:50]
    clean_slug = re.sub(r'^(clip-\d+|job-\d+)-?', '', clean_slug).strip('-')
    if not clean_slug or len(clean_slug) < 5:
        clean_slug = "shocking-encounter-uncut-breakdown"
    slug = f"{clean_slug}-{abs(hash(clip_filename)) % 100000}"

    # 6. Publish lên CMS qua WebsiteArticleService kèm Hero Image (Hook Thumbnail)
    svc = WebsiteArticleService(str(cfg_file))
    res = svc.publish_article(
        title=seo_title,
        slug=slug,
        body_html=body_html,
        image_url=hero_img,
        dry_run=False,
    )
    article_url = res.get("article_url")
    if res.get("status") != "success" or not article_url:
        raise WebsiteServiceError("CMS không xác nhận bài viết đã được tạo")
    svc.verify_article(article_url)

    return article_url, hero_img
