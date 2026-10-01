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
from multi_pc.data_root import canonical_data_root
from src.llm_response import chat_text_from_response, json_from_chat_response

logger = logging.getLogger("website_publisher")

HVS_DIR = Path(__file__).resolve().parent.parent.parent
DATA_ROOT = canonical_data_root()
sys.path.insert(0, str(HVS_DIR))


def _runtime_data_root() -> Path:
    """Resolve mutable config from the active installation root.

    Keeping the HVS_DIR fallback preserves isolated test/install roots while still
    enforcing the canonical-data-root guard when an explicit environment root is set.
    """
    return canonical_data_root(allow_repo_fallback=HVS_DIR)

try:
    from core.website_article_service import WebsiteArticleService, WebsiteServiceError, _BackendSession
    HAS_WEBSITE_SVC = True
except Exception as exc:
    WebsiteServiceError = RuntimeError
    logger.error("WebsiteArticleService import failed: %s", exc)
    HAS_WEBSITE_SVC = False

def get_website_config():
    """Lấy config CMS website được lưu cục bộ trong HVS."""
    cfg_file = DATA_ROOT / "config" / "website_config.json"
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
        with open(_runtime_data_root() / "config.json", "r", encoding="utf-8") as f:
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
        with open(_runtime_data_root() / "config.json", "r", encoding="utf-8") as f:
            root_cfg = json.load(f)
    except Exception:
        root_cfg = {}
    image_cfg = root_cfg.get("image_provider") if isinstance(root_cfg.get("image_provider"), dict) else {}
    llm_cfg = root_cfg.get("llm") if isinstance(root_cfg.get("llm"), dict) else {}
    api_base = str(image_cfg.get("api_base") or llm_cfg.get("api_base") or "").strip()
    generation_url = str(image_cfg.get("generation_url") or "").strip()
    configured_model = str(image_cfg.get("model") or "").strip()
    if not configured_model:
        task_models = llm_cfg.get("task_models") if isinstance(llm_cfg.get("task_models"), dict) else {}
        configured_model = str(task_models.get("image") or "").strip()
    requested_model = str(model_override or "").strip()
    if requested_model == "__video_frame__" or (not requested_model and configured_model == "__video_frame__"):
        selected_model = "__video_frame__"
    else:
        selected_model = requested_model or configured_model
    return {
        "api_base": api_base,
        "generation_url": generation_url,
        "models_url": str(image_cfg.get("models_url") or "").strip(),
        "api_key": str(image_cfg.get("api_key") or llm_cfg.get("api_key") or "").strip(),
        "model": selected_model,
    }

def _llm_headers(api_key: str) -> dict:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if api_key:
        headers.update({"Authorization": f"Bearer {api_key}", "x-api-key": api_key, "api-key": api_key})
    return headers


def _safe_text_llm_error(exc):
    from src.content_packages import sanitize_error
    return sanitize_error(exc) if isinstance(exc, (ValueError, RuntimeError)) else type(exc).__name__


def _text_chat_request(api_base, api_key, model, payload, timeout):
    from src.text_llm_diagnostics import chat_endpoint, chat_failure

    if not api_base:
        raise ValueError("Text LLM api_base missing: configure llm.api_base for the text route")
    if not model or not api_key:
        raise ValueError(chat_failure(None, has_key=bool(api_key), has_model=bool(model)))
    response = requests.post(chat_endpoint(api_base), headers=_llm_headers(api_key), json=payload, timeout=timeout)
    if response.status_code != 200:
        raise RuntimeError(chat_failure(response.status_code, has_key=True, has_model=True))
    return response


def _image_response_values(payload) -> list:
    """Extract provider image URL/base64 values from OpenAI-style and nested chat responses."""
    values = []

    def add(value):
        if isinstance(value, str):
            text = value.strip()
            data_match = re.search(r"data:image/[^;]+;base64,([A-Za-z0-9+/=\r\n]+)", text)
            if data_match:
                values.append(data_match.group(1).replace("\r", "").replace("\n", ""))
            for match in re.finditer(r"https?://[^\s)\]>'\"]+", text):
                values.append(match.group(0).rstrip(".,;"))

    def walk(value, key=""):
        if isinstance(value, dict):
            for child_key, child in value.items():
                lower_key = str(child_key).lower()
                if lower_key in ("url", "b64_json", "base64", "image_url"):
                    if isinstance(child, str):
                        if lower_key in ("b64_json", "base64"):
                            values.append(child.strip())
                        else:
                            add(child)
                    else:
                        walk(child, lower_key)
                elif lower_key in ("data", "images", "image", "choices", "message", "content", "output"):
                    walk(child, lower_key)
        elif isinstance(value, list):
            for child in value:
                walk(child, key)
        elif isinstance(value, str) and key in ("content", "output", "image", "image_url"):
            add(value)

    walk(payload)
    return list(dict.fromkeys(value for value in values if value))

def get_clip_metadata(clip_filename: str) -> dict:
    """
    Tìm thông tin video gốc từ jobs.json hoặc crawled_videos.json.
    Tuyệt đối loại bỏ triệt để mọi chữ 'Clip 1', 'Clip 2', 'job_...', 'Video Highlight'.
    """
    data_root = _runtime_data_root()
    jobs_file = data_root / "jobs.json"
    crawled_file = data_root / "crawled_videos.json"

    meta = {
        "clip_filename": clip_filename,
        "clean_title": "",
        "video_title": "",
        "youtube_url": "",
        "job_id": "",
        "clip_index": "",
        "description": "",
        "youtube_id": "",
        "long_video_path": "",
        "source_video_path": "",
        "clip_start": None,
        "clip_end": None,
        "clip_title": ""
    }

    # 1. Tìm trong jobs.json
    matched_job = None
    requested = Path(str(clip_filename or "")).expanduser()
    requested_resolved = str(requested.resolve(strict=False)).lower()
    requested_name = requested.name.lower()

    def _clip_matches(value):
        candidate = str(value or "").strip()
        if not candidate:
            return False
        path = Path(candidate).expanduser()
        return (str(path.resolve(strict=False)).lower() == requested_resolved
                or path.name.lower() == requested_name)

    if jobs_file.exists():
        try:
            with open(jobs_file, "r", encoding="utf-8", errors="ignore") as f:
                jobs = json.load(f)
                for j in jobs:
                    for c in j.get("clips", []):
                        if _clip_matches(c.get("filename")):
                            matched_job = j
                            meta["job_id"] = j.get("id") or ""
                            meta["clip_index"] = c.get("clip_index") or c.get("index") or ""
                            meta["youtube_url"] = j.get("youtube_url") or ""
                            meta["clip_start"] = c.get("start", c.get("start_time"))
                            meta["clip_end"] = c.get("end", c.get("end_time"))
                            meta["clip_title"] = c.get("title") or ""
                            meta["source_video_path"] = j.get("video_path") or ""
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
        long_path = data_root / "downloads" / f"{meta['job_id']}.mp4"
        if long_path.exists():
            meta["long_video_path"] = str(long_path)
    source_path = Path(str(meta.get("source_video_path") or ""))
    if not source_path.is_absolute():
        source_path = data_root / source_path
    if source_path.is_file() and source_path.suffix.lower() in (".mp4", ".mov", ".mkv", ".webm"):
        meta["source_video_path"] = str(source_path)
    elif meta.get("long_video_path"):
        meta["source_video_path"] = meta["long_video_path"]

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

def extract_youtube_video_id(value: str) -> str:
    """Extract a canonical YouTube video ID from a URL or raw ID."""
    raw = str(value or "").strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", raw):
        return raw
    patterns = (
        r"(?:youtube\.com/(?:watch\?(?:[^#]*&)?v=|embed/|shorts/|live/)|youtu\.be/)([A-Za-z0-9_-]{11})",
        r"[?&]v=([A-Za-z0-9_-]{11})",
    )
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return ""

def build_youtube_embed_html(youtube_id: str, title: str = "") -> str:
    """Build a responsive, privacy-enhanced YouTube iframe block."""
    clean_id = extract_youtube_video_id(youtube_id)
    if not clean_id:
        raise WebsiteServiceError("Link YouTube không có video ID hợp lệ")
    safe_title = html.escape(str(title or "YouTube video"), quote=True)
    embed_url = f"https://www.youtube-nocookie.com/embed/{clean_id}"
    return f"""
        <div class="youtube-embed-container" style="position: relative; width: 100%; max-width: 760px; margin: 0 auto; padding-bottom: 56.25%; height: 0; overflow: hidden; border-radius: 12px; background: #000; box-shadow: 0 4px 20px rgba(0,0,0,0.5);">
          <iframe src="{embed_url}" title="{safe_title}" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen style="position: absolute; inset: 0; width: 100%; height: 100%; border: 0;"></iframe>
        </div>
    """

def _valid_image_file(path: str, *, landscape: bool = False) -> bool:
    if not path or not os.path.isfile(path) or os.path.getsize(path) < 256:
        return False
    if not HAS_CV2:
        return True
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None or image.shape[0] < 120 or image.shape[1] < 160:
        return False
    return not landscape or image.shape[1] / max(1, image.shape[0]) >= 1.45


def _candidate_frame_times(video_path: str, clip_start=None, clip_end=None) -> list[float]:
    cap = cv2.VideoCapture(str(video_path))
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
    count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.release()
    duration = count / fps if fps > 0 else 0.0
    try:
        start = max(0.0, float(clip_start)) if clip_start is not None else None
        end = min(duration, float(clip_end)) if clip_end is not None and duration else None
    except (TypeError, ValueError):
        start = end = None
    if start is None:
        start = duration * 0.35 if duration else 0.0
    if end is None or end <= start:
        end = min(duration, start + max(8.0, duration * 0.12)) if duration else start + 8.0
    span = max(0.5, end - start)
    return sorted(set(round(max(0.0, min(start + span * offset, max(0.0, duration - 0.05))), 3) for offset in (0.08, 0.25, 0.42, 0.60, 0.78, 0.92)))


def _score_frame(frame) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    brightness = float(gray.mean()) / 255.0
    contrast = min(1.0, float(gray.std()) / 72.0)
    sharpness = min(1.0, float(cv2.Laplacian(gray, cv2.CV_64F).var()) / 900.0)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    saturation = min(1.0, float(hsv[:, :, 1].mean()) / 150.0)
    balanced = max(0.0, 1.0 - abs(brightness - 0.48) / 0.48)
    return 0.38 * sharpness + 0.22 * contrast + 0.20 * balanced + 0.20 * saturation


def select_smart_video_frame(video_path: str, clip_start=None, clip_end=None, output_path: str = "") -> str:
    """Choose a sharp, balanced 16:9 frame from the original source video."""
    if not HAS_CV2 or not video_path or not os.path.exists(video_path):
        return ""
    cap = cv2.VideoCapture(str(video_path))
    best = None
    for timestamp in _candidate_frame_times(video_path, clip_start, clip_end):
        cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000.0)
        ok, frame = cap.read()
        if ok:
            score = _score_frame(frame)
            if best is None or score > best[0]:
                best = score, frame
    cap.release()
    if best is None:
        return ""
    frame = best[1]
    height, width = frame.shape[:2]
    target = 16 / 9
    if width / max(1, height) > target:
        crop_width = int(height * target)
        frame = frame[:, max(0, (width - crop_width) // 2):][:, :crop_width]
    else:
        crop_height = int(width / target)
        frame = frame[max(0, (height - crop_height) // 2):][:crop_height, :]
    destination = Path(output_path or (HVS_DIR / "temp" / "smart_hero_frame.jpg"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    return str(destination) if cv2.imwrite(str(destination), frame, [cv2.IMWRITE_JPEG_QUALITY, 93]) and _valid_image_file(str(destination), landscape=True) else ""


def render_local_title_overlay(frame_path: str, title: str, output_path: str = "") -> str:
    """Add a deterministic title to a validated source frame."""
    if not HAS_CV2 or not _valid_image_file(frame_path, landscape=True):
        return ""
    image = cv2.imread(str(frame_path), cv2.IMREAD_COLOR)
    overlay = image.copy()
    height = image.shape[0]
    cv2.rectangle(overlay, (0, int(height * 0.66)), (image.shape[1], height), (8, 18, 34), -1)
    image = cv2.addWeighted(overlay, 0.82, image, 0.18, 0)
    clean = " ".join(str(title or "The Moment Everyone Missed").split())[:96]
    lines, line = [], ""
    for word in clean.split():
        if line and len(line) + len(word) + 1 > 30:
            lines.append(line)
            line = word
        else:
            line = (line + " " + word).strip()
    if line:
        lines.append(line)
    destination = Path(output_path or (HVS_DIR / "temp" / "smart_hero_overlay.jpg"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    y = int(height * 0.77)
    for index, text in enumerate(lines[:2]):
        point = (38, y + index * 58)
        cv2.putText(image, text.upper(), point, cv2.FONT_HERSHEY_DUPLEX, 1.25, (255, 255, 255), 3, cv2.LINE_AA)
        cv2.putText(image, text.upper(), point, cv2.FONT_HERSHEY_DUPLEX, 1.25, (32, 166, 255), 1, cv2.LINE_AA)
    return str(destination) if cv2.imwrite(str(destination), image, [cv2.IMWRITE_JPEG_QUALITY, 93]) and _valid_image_file(str(destination), landscape=True) else ""


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
    generation_url = image_cfg["generation_url"]
    api_key = image_cfg["api_key"]
    model = image_cfg["model"]
    if model == "__video_frame__" or (not generation_url and not api_base) or not model:
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
    import hashlib
    out_file = str(temp_dir / f"llm_hook_{hashlib.sha256(video_title.encode('utf-8')).hexdigest()[:16]}.jpg")

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
            if _valid_image_file(out_file, landscape=True):
                logger.info("Generated image-provider Hook Image: %s", out_file)
                return out_file
            Path(out_file).unlink(missing_ok=True)
            return ""
        except Exception as exc:
            logger.warning("Cannot save generated image response: %s", exc)
            return ""

    image_payload = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": "auto",
        "quality": "auto",
        "background": "auto",
        "image_detail": "high",
        "output_format": "png",
    }
    exact_url = generation_url.rstrip("/") if generation_url else f"{api_base.rstrip('/')}/images/generations"
    if not exact_url.lower().split("?", 1)[0].endswith("/v1/images/generations"):
        logger.warning("Image generation URL must end with /v1/images/generations: %s", exact_url)
        return ""
    attempts = [(exact_url, image_payload)]
    for url, payload in attempts:
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            if resp.status_code != 200:
                logger.warning("Image provider %s returned HTTP %s", url, resp.status_code)
                continue
            for image_value in _image_response_values(resp.json()):
                saved = save_image_value(image_value)
                if saved:
                    return saved
        except Exception as exc:
            logger.warning("Image provider request failed at %s: %s", url, exc)

    return ""

def upload_long_video_to_public_stream(meta: dict, clip_filename: str) -> str:
    """
    Upload a local original only through the configured video transport.
    The CMS image presign endpoint must never receive an MP4.
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
    public_url = svc.upload_video(str(target_video_file))
    svc.verify_public_media(public_url, require_range=True)
    return public_url

def extract_and_upload_article_assets(clip_filename: str, video_title: str) -> tuple:
    """Use the original long-form source for non-AI hero and article images."""
    _, cfg_file = get_website_config()
    if not HAS_WEBSITE_SVC or not cfg_file.exists():
        return "", []
    svc = WebsiteArticleService(str(cfg_file))
    sess = _BackendSession(svc.cfg)
    svc._ensure_session(sess)
    meta = get_clip_metadata(clip_filename)
    youtube_id = extract_youtube_video_id(meta.get("youtube_id") or meta.get("youtube_url"))
    source_path = next((str(path) for path in (
        meta.get("source_video_path"), meta.get("long_video_path")
    ) if path and Path(path).is_file()), "")
    hero = ""
    if get_image_provider_config()["model"] != "__video_frame__":
        generated = generate_llm_hook_image(video_title)
        if generated and _valid_image_file(generated, landscape=True):
            try:
                hero = svc._presign_and_upload(sess, generated) or ""
            except Exception as exc:
                logger.warning("AI hook upload failed: %s", exc)

    images = []
    if source_path:
        # Never silently crop the short portrait highlight into a fake landscape image.
        for index, (start, end) in enumerate(((meta.get("clip_start"), meta.get("clip_end")), (None, None))):
            frame = select_smart_video_frame(source_path, start, end,
                str(HVS_DIR / "temp" / f"source_frame_{Path(clip_filename).stem}_{index}.jpg"))
            if not frame:
                continue
            try:
                url = svc._presign_and_upload(sess, frame)
                if url:
                    images.append(url)
            except Exception as exc:
                logger.warning("Original-source frame upload failed: %s", exc)
    if not hero and images:
        hero = images[0]
    if not hero and youtube_id:
        hero = f"https://i.ytimg.com/vi/{youtube_id}/hqdefault.jpg"
    if not hero:
        raise WebsiteServiceError("Không có ảnh ngang từ video gốc hoặc YouTube; không dùng frame clip dọc")
    if not images and youtube_id:
        images = [f"https://i.ytimg.com/vi/{youtube_id}/hqdefault.jpg"]
    return hero, images[:2]

def generate_deep_article_content(video_title: str, hero_img: str, body_imgs: list, video_stream_url: str = "", youtube_id: str = "") -> tuple:
    """
    Sinh bài viết dài chuyên sâu 500+ từ chuẩn báo chí quốc tế:
    - ĐẦU BÀI: Hiển thị ngay tấm ảnh Hook LLM to sắc nét (Hero Banner)!
    - Mở đầu lôi cuốn
    - 2 phần phân tích chuyên sâu + ảnh minh họa diễn biến
    - CUỐI BÀI: Ưu tiên YouTube iframe; giữ HTML5 MP4 làm fallback cho job cũ.
    """
    clean_youtube_id = extract_youtube_video_id(youtube_id)
    if clean_youtube_id:
        video_player_html = build_youtube_embed_html(clean_youtube_id, video_title)
        source_label = "Original YouTube Video"
    elif video_stream_url and str(video_stream_url).startswith("https://"):
        safe_stream_url = html.escape(str(video_stream_url), quote=True)
        safe_poster = html.escape(str(hero_img or ""), quote=True)
        video_player_html = f"""
        <div style="margin: 0 auto; max-width: 760px; border-radius: 12px; overflow: hidden; background: #000; box-shadow: 0 4px 20px rgba(0,0,0,0.5);">
          <video controls playsinline preload="metadata" poster="{safe_poster}" style="width: 100%; max-height: 520px; display: block; outline: none;">
            <source src="{safe_stream_url}" type="video/mp4">
            Trình duyệt của bạn không hỗ trợ phát video trực tiếp.
          </video>
        </div>
        """
        source_label = "Official Broadcast Stream"
    else:
        raise WebsiteServiceError("Video chưa có YouTube ID hoặc HTTPS public URL hợp lệ")
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
          <p style="font-size: 13px; color: #64748b; margin-top: 6px; font-style: italic;">Reference frame from the original source video; compare with the complete sequence below.</p>
        </div>
        """
    
    img_late_html = ""
    if body_imgs and len(body_imgs) > 1:
        img_late_html = f"""
        <div style="margin: 24px 0; text-align: center;">
          <img src="{body_imgs[1]}" alt="{title} dramatic climax" style="width: 100%; max-width: 720px; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.12);">
          <p style="font-size: 13px; color: #64748b; margin-top: 6px; font-style: italic;">Another source-video frame for context, not independent evidence of an outcome.</p>
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
    # No-LLM copy must not invent a play, reaction, athlete or outcome absent
    # from source metadata. Provide a substantial viewing guide instead.
    lead = (f"This page brings together the original full-length video associated with '{title}' and a guide to watching it closely. "
            "The title identifies the subject, but it cannot establish what happened on screen or how anyone reacted. "
            "Use the complete recording below to assess the sequence in its own context rather than relying on a short excerpt or an unverified account.")
    s1_title = "How to examine the original sequence"
    s1_content = ("Start with the beginning of the source recording and note where the relevant sequence starts. "
                  "Look at what is visible before the moment highlighted by the title, including the camera angle, the number of people in frame and any on-screen labels. "
                  "Those details help establish context but should not be treated as proof of a claim that the recording does not show.\n"
                  "On a second viewing, pause at the start and end of the sequence. Compare those frames with the intervening footage rather than inferring a cause from a single still. "
                  "If an edit, replay or camera change appears, distinguish it from continuous footage. The original video embedded on this page is the primary reference for these checks; the accompanying images are viewing aids, not independent evidence.")
    s2_title = "What the footage can and cannot confirm"
    s2_content = ("A recording can show actions within its frame, but it does not by itself identify motives, establish events outside the frame or verify claims about audience reaction. "
                  "Check the surrounding minutes for context before drawing a conclusion from the selected moment. If a detail remains unclear, describe it as unclear rather than filling the gap with a confident explanation.\n"
                  "The images in this article come from the original horizontal source or its source-video thumbnail when available. They offer reference points for returning to the longer recording, not substitutes for it. "
                  "Watch the full video below, compare the beginning, middle and end of the relevant passage, and decide which observations are directly supported. "
                  "Without corroborating sources, this article intentionally does not assert a final outcome, a specific tactical explanation or a quote from any participant.")

    try:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You write structured, thorough journalistic feature articles. Respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1800,
            "temperature": 0.7
        }
        resp = _text_chat_request(api_base, api_key, model, payload, 60)
        if resp.status_code == 200:
            d = json_from_chat_response(resp)
            if not isinstance(d, dict):
                raise ValueError("LLM article response is not an object")
            seo_title = d.get("seo_title") or seo_title
            lead = d.get("lead_paragraph") or lead
            s1_title = d.get("section_1_title") or s1_title
            s1_content = d.get("section_1_content") or s1_content
            s2_title = d.get("section_2_title") or s2_title
            s2_content = d.get("section_2_content") or s2_content
    except Exception as exc:
        logger.warning("LLM deep article generation failed: %s", _safe_text_llm_error(exc))

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
          Review the available original recording below and compare the sequence with the surrounding context.
        </p>
        
        {video_player_html}
        
        <div style="font-size: 12px; color: #64748b; margin-top: 14px;">
          {source_label} • Full HD • All Rights Reserved
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
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You write viral, curiosity-piquing first comments in English. Return only the final comment text."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 120,
            "temperature": 0.8
        }
        resp = _text_chat_request(api_base, api_key, model, payload, 45)
        if resp.status_code == 200:
            comment = chat_text_from_response(resp).strip()
            if not comment:
                raise ValueError("LLM comment response is empty")
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
            logger.warning("LLM comment gen error: %s", resp.status_code)
    except Exception as exc:
        logger.warning("LLM comment gen exception (using fallback): %s", _safe_text_llm_error(exc))

    return fallback_comment

def publish_clip_to_website_cms(clip_filename: str, video_title: str = None) -> tuple:
    """
    Tự động:
    1. Nhúng VIDEO GỐC bằng YouTube iframe; chỉ upload MP4 khi job cũ không có YouTube ID
    2. Tạo ảnh HOOK AI bằng LLM (gemini-3.1-flash-image) chuẩn hình mẫu boss gửi (chữ 3D đỏ to, banner vàng, vòng tròn đỏ, icon REC) và upload CDN
    3. ĐẶT ẢNH HOOK NGAY ĐẦU BÀI VIẾT và làm Thumbnail đại diện bài viết (og:image)
    4. Viết bài chuyên sâu 500+ từ, đặt YouTube embed hoặc MP4 fallback ở cuối bài
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

    # 2. Ưu tiên nhúng YouTube gốc để không lưu MP4 trên server. Chỉ upload
    # video dài làm fallback cho các job cũ không có nguồn YouTube hợp lệ.
    youtube_id = extract_youtube_video_id(meta.get("youtube_id")) or extract_youtube_video_id(meta.get("youtube_url"))
    video_stream_url = ""
    if not youtube_id:
        video_stream_url = upload_long_video_to_public_stream(meta, clip_filename)
        if not video_stream_url:
            raise WebsiteServiceError("Không có YouTube ID và upload video không trả public URL")

    # 3. Tạo ảnh HOOK AI bằng LLM & Trích xuất ảnh minh họa
    hero_img, body_imgs = extract_and_upload_article_assets(clip_filename, video_title)

    # 4. Sinh bài viết chi tiết, có ảnh Hook ngay đầu bài và Video Player Full ở CUỐI bài
    seo_title, body_html = generate_deep_article_content(
        video_title, hero_img, body_imgs, video_stream_url=video_stream_url, youtube_id=youtube_id
    )

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
    svc.verify_article_embed(article_url, youtube_id=youtube_id, video_stream_url=video_stream_url)

    return article_url, hero_img
