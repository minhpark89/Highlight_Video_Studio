import os
import sys
import json
import re
import html
import hashlib
from urllib.parse import urlparse
try:
    import cv2
    HAS_CV2 = True
except Exception:
    HAS_CV2 = False
try:
    from PIL import Image
except Exception:
    Image = None
import subprocess
import logging
from pathlib import Path
import requests
from multi_pc.data_root import canonical_data_root
from src.llm_response import chat_model_unavailable, chat_stream_incomplete, chat_text_from_response, json_from_chat_response
from src.english_text import ENGLISH_INSTRUCTION, assert_english, assert_english_package, english_or_default, is_english

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
    # Ask the provider for a single completed JSON envelope. Some gateways
    # still return SSE; reject a truncated HTTP 200 rather than using its text.
    response = requests.post(chat_endpoint(api_base), headers=_llm_headers(api_key),
                             json={**payload, "stream": False}, timeout=timeout)
    if response.status_code != 200:
        raise RuntimeError(chat_failure(response.status_code, has_key=True, has_model=True))
    if chat_stream_incomplete(response):
        raise RuntimeError("Text LLM stream ended without completion")
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

def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verified_foreign_source(clip_filename: str, data_root: Path) -> Path | None:
    """Resolve a selected foreign clip or a staged clip using recorded byte provenance.

    A filename alone is never evidence that a foreign job owns a staged clip.
    """
    selected = Path(str(clip_filename or "")).expanduser()
    staged = selected if selected.is_absolute() else data_root / "output" / selected
    try:
        if staged.is_symlink():
            return None
        staged = staged.resolve(strict=True)
        if staged.is_symlink() or not staged.is_file() or staged.suffix.lower() != ".mp4":
            return None
        local_output = (data_root / "output").resolve()
        if staged.parent != local_output:
            return staged if staged.parent.name.lower() == "output" else None

        # The scheduler records the original path and the digest of the staged bytes.
        # Verify both, plus the source-identity key encoded in the staging filename.
        posts_file = data_root / "posts.json"
        if not posts_file.is_file():
            return None
        posts = json.loads(posts_file.read_text(encoding="utf-8"))
        if not isinstance(posts, list):
            return None
        for post in posts:
            if not isinstance(post, dict):
                continue
            media = Path(str(post.get("media_file") or ""))
            media = media if media.is_absolute() else local_output / media
            if media.resolve(strict=False) != staged:
                continue
            sha = str(post.get("source_sha256") or "").lower()
            source = Path(str(post.get("source_video_path") or "")).expanduser()
            if not re.fullmatch(r"[a-f0-9]{64}", sha) or not source.is_absolute():
                continue
            if source.is_symlink() or not source.is_file() or source.parent.name.lower() != "output":
                continue
            source = source.resolve(strict=True)
            if source.parent == local_output:
                continue
            identity = os.path.normcase(str(source))
            key = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
            if staged.name != f"source-{key}-{sha}{source.suffix.lower()}":
                continue
            if _file_sha256(staged) == sha and _file_sha256(source) == sha:
                return source
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None
    return None


def get_clip_metadata(clip_filename: str) -> dict:
    """
    Tìm thông tin video gốc từ jobs.json hoặc crawled_videos.json.
    Tuyệt đối loại bỏ triệt để mọi chữ 'Clip 1', 'Clip 2', 'job_...', 'Video Highlight'.
    """
    data_root = _runtime_data_root()
    from src.video_recovery_media import recovery_source
    recovered = recovery_source(data_root, clip_filename)
    if recovered is not None:
        return recovered
    jobs_file = data_root / "jobs.json"
    crawled_file = data_root / "crawled_videos.json"
    foreign_source = _verified_foreign_source(clip_filename, data_root)
    if foreign_source is not None:
        # Only a job ledger next to the *verified* source output folder is eligible.
        # Never search arbitrary foreign installations by matching a basename.
        jobs_file = foreign_source.parent.parent / "jobs.json"
        crawled_file = foreign_source.parent.parent / "crawled_videos.json"

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
    requested = foreign_source or Path(str(clip_filename or "")).expanduser()
    if not requested.is_absolute() and requested.parent == Path("."):
        requested = data_root / "output" / requested
    requested_resolved = str(requested.resolve(strict=False)).lower()
    requested_name = requested.name.lower()

    def _clip_matches(value):
        candidate = str(value or "").strip()
        if not candidate:
            return False
        path = Path(candidate).expanduser()
        if path.name.lower() != requested_name:
            return False
        if path.is_absolute():
            return (requested.is_file()
                    and path.parent.resolve(strict=False) == (jobs_file.parent / "output").resolve(strict=False)
                    and str(path.resolve(strict=False)).lower() == requested_resolved)
        # A bare job clip name is meaningful only inside its own output directory.
        return (requested.is_file()
                and requested.parent.resolve(strict=False) == (jobs_file.parent / "output").resolve(strict=False)
                and path.name.lower() == requested_name and path.name == candidate)

    if jobs_file.exists():
        try:
            from src.job_store import load as load_job_rows
            jobs = load_job_rows(jobs_file)
            matches = []
            for j in jobs if isinstance(jobs, list) else []:
                if not isinstance(j, dict):
                    continue
                for c in j.get("clips", []):
                    if isinstance(c, dict) and _clip_matches(c.get("filename")):
                        matches.append((j, c))
                        break
            if len(matches) == 1:
                matched_job, c = matches[0]
                meta["job_id"] = matched_job.get("id") or ""
                meta["clip_index"] = c.get("clip_index") or c.get("index") or ""
                meta["youtube_url"] = matched_job.get("youtube_url") or ""
                meta["clip_start"] = c.get("start", c.get("start_time"))
                meta["clip_end"] = c.get("end", c.get("end_time"))
                meta["clip_title"] = c.get("title") or ""
                meta["source_video_path"] = matched_job.get("video_path") or ""
                meta["description"] = matched_job.get("description") or ""
                meta["source_transcript_excerpt"] = matched_job.get("source_transcript_excerpt") or ""
                vt = (matched_job.get("video_title") or "").strip()
                if vt and not re.search(r'^(video highlight|job_\d+|clip_\d+)', vt, re.IGNORECASE):
                    meta["video_title"] = vt
            elif len(matches) > 1:
                logger.warning("Ambiguous clip metadata for %s in %s", requested, jobs_file)
        except Exception:
            pass

    # 2. Tìm youtube_id
    y_url = meta.get("youtube_url", "")
    meta["youtube_id"] = extract_youtube_video_id(y_url)

    # Kiểm tra file video gốc dài trong downloads/
    if meta.get("job_id"):
        long_path = jobs_file.parent / "downloads" / f"{meta['job_id']}.mp4"
        if long_path.exists():
            meta["long_video_path"] = str(long_path)
    source_path = Path(str(meta.get("source_video_path") or ""))
    if not source_path.is_absolute():
        source_path = jobs_file.parent / source_path
    if source_path.is_file() and source_path.suffix.lower() in (".mp4", ".mov", ".mkv", ".webm"):
        meta["source_video_path"] = str(source_path)
    elif meta.get("long_video_path"):
        meta["source_video_path"] = meta["long_video_path"]

    # 3. Tìm ngược sang crawled_videos.json để lấy title video thật
    if crawled_file.exists():
        try:
            with open(crawled_file, "r", encoding="utf-8", errors="ignore") as f:
                crawled = json.load(f)
                for cv in crawled:
                    if (y_url and cv.get("url") == y_url) or (meta["youtube_id"] and cv.get("id") == meta["youtube_id"]):
                        if not meta["video_title"] or len(meta["video_title"]) < 10:
                            meta["video_title"] = cv.get("title") or meta["video_title"]
                        meta["description"] = cv.get("description") or meta["description"]
                        break
        except Exception:
            pass

    # 4. Lọc sạch triệt để: KHÔNG BAO GIỜ ĐỂ CHỮ "Clip 1", "Clip 2", "job_..."
    v_clean = meta["video_title"]
    v_clean = re.sub(r'^(Video Highlight|job_\d+_[a-f0-9]+|clip[_\s\-]*\d+)\s*', '', v_clean, flags=re.IGNORECASE).strip()
    
    # Nếu vẫn bị trống hoặc còn là mã rác (VD: "Clip 2", "job_...") -> Đặt tiêu đề giật gân tự nhiên
    if not v_clean or len(v_clean) < 8 or re.match(r'^(clip|job|highlight)', v_clean, re.IGNORECASE):
        v_clean = "Original Video and Full Recording Guide"

    meta["video_title"] = v_clean.title()
    meta["clean_title"] = meta["video_title"]

    return meta

def source_transcript_excerpt(segments) -> str:
    snippets = [str(item.get("text") or "").strip() if isinstance(item, dict)
                else str(getattr(item, "text", "") or "").strip() for item in segments]
    snippets = [text for text in snippets if text]
    if not snippets:
        return ""
    excerpts = []
    for position in (0, len(snippets) // 2, max(0, len(snippets) - 10)):
        excerpt = " ".join(snippets[position:position + 8])[:600]
        if excerpt and excerpt not in excerpts:
            excerpts.append(excerpt)
    return " | ".join(excerpts)[:1800]


def _source_video_summary(meta: dict, title: str) -> str:
    description = str(meta.get("description") or "").strip()
    if description:
        return description
    cached = str(meta.get("source_transcript_excerpt") or "").strip()
    if cached:
        return f"The original video, titled '{title}', includes these source transcript passages: {cached}"[:2400]
    ass_path = _runtime_data_root() / "temp" / f"{Path(str(meta.get('clip_filename') or '')).stem}.ass"
    if ass_path.is_file():
        try:
            lines = []
            seen = set()
            for raw in ass_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                if "Dialogue:" not in raw:
                    continue
                text = raw.split(",", 9)[-1]
                text = re.sub(r"\{[^}]*\}", "", text).strip()
                if text and text not in seen:
                    seen.add(text)
                    lines.append(text)
            if lines:
                return (f"The original recording is titled '{title}'. The clip transcript includes "
                        "these source phrases: " + " ".join(lines[:80]))[:1800]
        except OSError:
            pass
    youtube_id = extract_youtube_video_id(meta.get("youtube_id") or meta.get("youtube_url"))
    if youtube_id:
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            class TranscriptSession(requests.Session):
                def request(self, method, url, **kwargs):
                    kwargs.setdefault("timeout", (5, 15))
                    return super().request(method, url, **kwargs)
            with TranscriptSession() as session:
                transcript = YouTubeTranscriptApi(http_client=session).fetch(youtube_id)
            excerpts = source_transcript_excerpt(transcript)
            if excerpts:
                return (f"The original video, titled '{title}', includes these transcript passages "
                        "from the opening, middle and closing portions: " + excerpts)[:2400]
        except Exception as exc:
            logger.info("Original transcript unavailable: %s", type(exc).__name__)
    return (
        f"The original recording is titled '{title}'. No verified transcript or detailed description "
        "was available, so this page keeps the summary limited to what the source itself can establish."
    )


def extract_youtube_video_id(value: str) -> str:
    """Extract a canonical YouTube video ID from a URL or raw ID."""
    raw = str(value or "").strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", raw):
        return raw
    from urllib.parse import parse_qs, urlparse
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()
    if host in ("youtube.com", "www.youtube.com", "m.youtube.com", "youtube-nocookie.com", "www.youtube-nocookie.com"):
        candidate = (parse_qs(parsed.query).get("v") or [""])[0] if parsed.path == "/watch" else next(
            (part for prefix in ("/embed/", "/shorts/", "/live/") if parsed.path.startswith(prefix)
             for part in [parsed.path[len(prefix):].split("/", 1)[0]]), "")
    elif host in ("youtu.be", "www.youtu.be"):
        candidate = parsed.path.strip("/").split("/", 1)[0]
    else:
        candidate = ""
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
        return candidate
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
        if Image is None:
            return False
        try:
            with Image.open(path) as image:
                width, height = image.size
                return width >= 160 and height >= 120 and (not landscape or width / height >= 1.45)
        except Exception:
            return False
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
    if not video_path or not os.path.exists(video_path):
        return ""
    if not HAS_CV2:
        root = _runtime_data_root()
        ffprobe = next((str(p) for p in (root / "bin" / "ffprobe.exe", HVS_DIR / "bin" / "ffprobe.exe") if p.is_file()), "ffprobe")
        ffmpeg = next((str(p) for p in (root / "bin" / "ffmpeg.exe", HVS_DIR / "bin" / "ffmpeg.exe") if p.is_file()), "ffmpeg")
        try:
            info = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height:format=duration", "-of", "json", str(video_path)],
                capture_output=True, text=True, timeout=20, check=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            payload = json.loads(info.stdout)
            stream = (payload.get("streams") or [{}])[0]
            width, height = int(stream.get("width") or 0), int(stream.get("height") or 0)
            if not height or width <= height:
                return ""
            duration = float((payload.get("format") or {}).get("duration") or 0)
            start = float(clip_start) if clip_start is not None else duration * 0.35
            end = float(clip_end) if clip_end is not None else duration * 0.65
            timestamp = max(0.0, min((start + end) / 2, max(0.0, duration - 0.1)))
            destination = Path(output_path or (HVS_DIR / "temp" / "smart_hero_frame.jpg"))
            destination.parent.mkdir(parents=True, exist_ok=True)
            crop_width = min(width, int(height * 16 / 9)) // 2 * 2
            crop_height = min(height, int(width * 9 / 16)) // 2 * 2
            subprocess.run([ffmpeg, "-y", "-ss", str(timestamp), "-i", str(video_path),
                "-vf", f"crop={crop_width}:{crop_height}",
                "-frames:v", "1", "-q:v", "2", str(destination)],
                capture_output=True, timeout=45, check=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return str(destination) if _valid_image_file(str(destination), landscape=True) else ""
        except (OSError, ValueError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
            logger.warning("Original source frame extraction failed: %s", type(exc).__name__)
            return ""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        cap.release()
        return ""
    # Reject a portrait source before cropping: a horizontal crop of a short
    # vertical highlight must never masquerade as an original landscape frame.
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    if not height or width <= height:
        cap.release()
        return ""
    best = None
    for timestamp in _candidate_frame_times(video_path, clip_start, clip_end):
        cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000.0)
        ok, frame = cap.read()
        if ok and frame.shape[1] > frame.shape[0]:
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

    prompt = f"""Create a 16:9 landscape editorial thumbnail for the original video titled "{video_title}".
Use only the subject implied by this title. Do not invent real people, events, outcomes, police scenes or bodycam footage unless the title specifically identifies them.
Use clear, readable headline typography based on the title, strong contrast, and an engaging visual composition.
The image should work as a website article hero. Do not include false claims or unrelated stock scenes."""

    headers = _llm_headers(api_key)
    temp_dir = HVS_DIR / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    import hashlib
    cache_key = f"{model}\n{generation_url or api_base}\n{video_title}"
    out_file = str(temp_dir / f"llm_hook_{hashlib.sha256(cache_key.encode('utf-8')).hexdigest()[:16]}.jpg")
    if Path(out_file).is_file() and _valid_image_file(out_file, landscape=True):
        return out_file

    def save_image_value(value) -> str:
        if not value:
            return ""
        if isinstance(value, dict):
            value = value.get("url") or value.get("b64_json")
        value = str(value)
        import uuid
        from multi_pc.json_io import replace_with_retry
        candidate = Path(out_file).with_name(f".{Path(out_file).stem}.{uuid.uuid4().hex}.jpg")
        try:
            if value.startswith("http://") or value.startswith("https://"):
                downloaded = requests.get(value, timeout=90)
                downloaded.raise_for_status()
                candidate.write_bytes(downloaded.content)
            else:
                raw_b64 = value.split("base64,", 1)[1] if "base64," in value else value
                candidate.write_bytes(base64.b64decode(raw_b64))
            # Some image gateways ignore the requested 16:9 composition and
            # return a square image. Keep the complete artwork/headline in a
            # landscape canvas instead of rejecting a successful generation.
            if Image is not None:
                try:
                    from PIL import ImageOps, ImageFilter
                    with Image.open(candidate) as picture:
                        if picture.width < 160 or picture.height < 120:
                            raise ValueError("Generated image dimensions too small")
                        foreground = picture.convert("RGB")
                    if abs(foreground.width / foreground.height - 16 / 9) > 0.03:
                        normalized = ImageOps.fit(foreground, (1280, 720)).filter(ImageFilter.GaussianBlur(24))
                        foreground.thumbnail((1280, 720), Image.Resampling.LANCZOS)
                        normalized.paste(foreground, ((1280 - foreground.width) // 2, (720 - foreground.height) // 2))
                    else:
                        normalized = ImageOps.fit(foreground, (1280, 720))
                    normalized.save(candidate, format="JPEG", quality=90, optimize=True)
                except Exception:
                    # _valid_image_file below remains the final decode gate.
                    pass
            if _valid_image_file(str(candidate), landscape=True):
                replace_with_retry(candidate, Path(out_file))
                logger.info("Generated image-provider Hook Image: %s", out_file)
                return out_file
            return ""
        except Exception as exc:
            logger.warning("Cannot save generated image response (%s); use source-frame fallback", type(exc).__name__)
            return ""
        finally:
            candidate.unlink(missing_ok=True)

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
        logger.warning("Image generation URL must end with /v1/images/generations; use source-frame fallback")
        return ""
    try:
        resp = requests.post(exact_url, headers=headers, json=image_payload, timeout=120)
    except requests.RequestException as exc:
        # Request exceptions can include the full authenticated URL or headers.
        logger.warning("Image provider transport failed (%s); use source-frame fallback", type(exc).__name__)
        return ""

    if resp.status_code != 200:
        # A gateway 502/5xx is not a client 4xx. Do not replay ambiguous image
        # generation: the upstream may have charged/completed it already.
        category = "upstream/gateway" if 500 <= resp.status_code <= 599 else "client/config" if 400 <= resp.status_code <= 499 else "unexpected"
        logger.warning("Image provider %s HTTP %s; use source-frame fallback", category, resp.status_code)
        return ""
    try:
        values = _image_response_values(resp.json())
    except (ValueError, TypeError):
        logger.warning("Image provider HTTP 200 returned invalid JSON; use source-frame fallback")
        return ""
    for image_value in values:
        saved = save_image_value(image_value)
        if saved:
            return saved
    logger.warning("Image provider HTTP 200 returned no usable landscape image; use source-frame fallback")

    return ""

def upload_long_video_to_public_stream(meta: dict, clip_filename: str) -> str:
    """
    Upload a local original only through the configured video transport.
    The CMS image presign endpoint must never receive an MP4.
    """
    long_path = meta.get("long_video_path")
    target_video_file = None
    target_stream_name = None

    clip_path = Path(str(clip_filename or ""))
    if not clip_path.is_absolute():
        clip_path = _runtime_data_root() / "output" / clip_path
    for candidate in (meta.get("source_video_path"), long_path):
        if candidate and Path(candidate).is_file() and Path(candidate).resolve() != clip_path.resolve():
            target_video_file = Path(candidate)
            break

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

def extract_and_upload_article_assets(clip_filename: str, video_title: str, *, mode="auto", metadata=None) -> tuple:
    """Upload a hero thumbnail and two source frames for the article.

    A configured image model gets first chance to create the hero thumbnail.
    The two body images always come from the original horizontal recording so
    the article keeps an auditable source trail when the image model is down.
    """
    _, cfg_file = get_website_config()
    if not HAS_WEBSITE_SVC or not cfg_file.exists():
        return "", []
    svc = WebsiteArticleService(str(cfg_file))
    sess = _BackendSession(svc.cfg)
    svc._ensure_session(sess)
    meta = get_clip_metadata(clip_filename)
    clip_path = Path(str(clip_filename or ""))
    if not clip_path.is_absolute():
        clip_path = _runtime_data_root() / "output" / clip_path
    source_path = next((str(path) for path in (
        meta.get("source_video_path"), meta.get("long_video_path")
    ) if path and Path(path).is_file() and Path(path).resolve() != clip_path.resolve()), "")
    images = []
    if source_path:
        # Sample three different windows from the horizontal original video.
        # The portrait Reel is deliberately excluded above.
        try:
            clip_start = float(meta.get("clip_start"))
            clip_end = float(meta.get("clip_end"))
            if clip_end <= clip_start:
                raise ValueError("invalid clip window")
            step = (clip_end - clip_start) / 3.0
            windows = [(clip_start + i * step, clip_start + (i + 1) * step) for i in range(3)]
        except (TypeError, ValueError):
            from src.media_validation import InvalidMedia, probe_video
            try:
                duration = probe_video(source_path)["duration"]
            except InvalidMedia:
                duration = 0
            windows = [(duration * i / 3, duration * (i + 1) / 3) for i in range(3)] if duration else []
        for index, (start, end) in enumerate(windows):
            frame = select_smart_video_frame(source_path, start, end,
                str(HVS_DIR / "temp" / f"source_frame_{Path(clip_filename).stem}_{index}.jpg"))
            if not frame or not _valid_image_file(frame, landscape=True):
                continue
            try:
                url = svc._presign_and_upload(sess, frame)
                if url and url not in images:
                    images.append(url)
            except Exception as exc:
                logger.warning("Original-source frame upload failed: %s", type(exc).__name__)
    if len(images) < 2:
        raise WebsiteServiceError("Cần 2 ảnh minh họa từ video dài gốc. Nguồn ngang 4:3 hoặc 16:9 đều hợp lệ; không dùng clip dọc.")
    hero = images[0]
    image_config = get_image_provider_config()
    if metadata is not None:
        metadata.update(image_source="source_frame", image_model="", image_fallback_reason="")
    # Text fallback mode does not disable the independent hero image model.
    if str(image_config.get("model") or "") != "__video_frame__":
        try:
            generated = generate_llm_hook_image(video_title)
            if generated and _valid_image_file(generated, landscape=True):
                uploaded_hook = svc._presign_and_upload(sess, generated)
                if uploaded_hook and uploaded_hook not in images:
                    hero = uploaded_hook
                    if metadata is not None:
                        metadata.update(image_source="image_model", image_model=image_config.get("model", ""))
                    logger.info("Article hero thumbnail source=image_model")
            elif metadata is not None:
                metadata["image_fallback_reason"] = "Model ảnh chưa trả ảnh hợp lệ; dùng frame video gốc."
        except Exception as exc:
            logger.info("Article hero image model unavailable; using source frame (%s)", type(exc).__name__)
            if metadata is not None:
                metadata["image_fallback_reason"] = "Model ảnh lỗi; dùng ảnh ngang từ video dài gốc."
    if hero == images[0] and len(images) < 3:
        raise WebsiteServiceError("Model ảnh chưa có ảnh hợp lệ; cần thêm frame thứ ba từ video dài gốc làm thumbnail dự phòng.")
    if metadata is not None:
        metadata.update(hero_image_url=hero, body_image_urls=images[:2] if hero != images[0] else images[1:3])
    return hero, images[:2] if hero != images[0] else images[1:3]


def render_content_package_article(video_title, hero_img, body_imgs, *, package,
                                   youtube_id="", video_stream_url="", source_summary=""):
    """Render the exact package used by the queue, with its images and player."""
    from src.article_format import normalize_article, paragraph_html, viewing_article, word_count, MIN_ARTICLE_WORDS
    assert_english_package(package)
    video_title = english_or_default(package.get("hero_title"), english_or_default(video_title, "Original Video"))
    source_summary = english_or_default(package.get("source_summary"), english_or_default(source_summary))
    article = normalize_article(package.get("article_html", ""))
    if word_count(article) < MIN_ARTICLE_WORDS:
        if package.get("required_llm"):
            raise WebsiteServiceError("Bài LLM chưa đủ 600 từ; chọn auto để dùng bài dự phòng hoặc thử lại.")
        article = viewing_article(video_title, source_summary, package.get("niche", ""))
        package["article_source"] = "no_llm_short_article"
        package["article_fallback_reason"] = "Bài LLM chưa đủ 600 từ; dùng bài theo tiêu đề và nguồn video."
    else:
        package["article_source"] = package.get("source", "unknown")
    package["article_html"] = article
    package["word_count"] = word_count(article)
    title = html.escape(str(video_title), quote=True)
    figure = lambda url, caption: (f'<figure style="margin:24px 0"><img src="{html.escape(str(url), quote=True)}" '
        f'alt="{title}" loading="lazy" style="width:100%;border-radius:12px">'
        f'<figcaption>{html.escape(caption)}</figcaption></figure>')
    blocks = re.findall(r'<(?:p|h2|h3)>.*?</(?:p|h2|h3)>', article, re.S)
    for index, url in reversed(list(enumerate(body_imgs[:2]))):
        position = max(1, int(len(blocks) * (index + 1) / 3))
        blocks.insert(position, figure(url, "Reference frame from the original video; watch the complete sequence below."))
    if youtube_id:
        player = build_youtube_embed_html(youtube_id, video_title)
    elif str(video_stream_url).startswith("https://"):
        player = (f'<video controls playsinline preload="metadata" poster="{html.escape(hero_img, quote=True)}" '
                  f'style="width:100%"><source src="{html.escape(video_stream_url, quote=True)}" type="video/mp4"></video>')
    else:
        raise WebsiteServiceError("Cần video YouTube gốc hoặc HTTPS video đã xác minh.")
    hero_caption = "Editorial illustration created with the configured image model." if package.get("image_source") == "image_model" else "Reference frame from the original recording."
    body = (f'<article class="article-content" style="max-width:820px;margin:auto;line-height:1.8">'
            f'{figure(hero_img, hero_caption)}<section class="original-video-summary"><h2>Original video summary</h2>'
            f'{paragraph_html(source_summary or "Follow the full recording below for the sequence behind this title.")}</section>'
            f'{"".join(blocks)}<section id="full-video" class="full-video-section"><h2>Full Uncut Footage</h2>'
            '<p>Watch the full video below and follow the sequence from beginning to end.</p>'
            f'{player}</section></article>')
    return package.get("hero_title") or video_title, body

def generate_deep_article_content(video_title: str, hero_img: str, body_imgs: list, video_stream_url: str = "", youtube_id: str = "", source_summary: str = "", prepared_package=None) -> tuple:
    """
    Sinh bài viết dài chuyên sâu 500+ từ chuẩn báo chí quốc tế:
    - ĐẦU BÀI: Hiển thị ngay tấm ảnh Hook LLM to sắc nét (Hero Banner)!
    - Mở đầu lôi cuốn
    - 2 phần phân tích chuyên sâu + ảnh minh họa diễn biến
    - CUỐI BÀI: Ưu tiên YouTube iframe; giữ HTML5 MP4 làm fallback cho job cũ.
    """
    if prepared_package is not None:
        return render_content_package_article(video_title, hero_img, body_imgs, package=prepared_package,
            youtube_id=youtube_id, video_stream_url=video_stream_url, source_summary=source_summary)
    original_title, original_summary = video_title, source_summary
    video_title = english_or_default(video_title, "Original Video")
    source_summary = english_or_default(source_summary)
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
1. "lead_paragraph": An engaging introduction grounded in the supplied title and source summary; do not invent stakes, reactions, quotes or an outcome.
2. "section_1_title": "The Decisive Breakdown: What Truly Unfolded"
3. "section_1_content": Explain the source context and what readers can review in the full video without unsupported claims.
4. "section_2_title": "Inside the Climax: Tactical Genius & Aftermath"
5. "section_2_content": Build curiosity around the source and invite readers to watch the full video at the end; use only supplied facts.
6. Make it thorough and captivating (750-950 words; never below 600 words), one sentence per paragraph.
Original source title (translate to English): {original_title}
Source summary (translate to English): {original_summary}
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
    s1_content += ("\nBegin by separating the title from the recording itself. The title is a locator for this source, not a transcript or a verified description of every frame. "
                   "Record the timestamp of any passage you want to discuss, then return to a little earlier in the same video to check what the camera had already established. "
                   "If the recording includes cuts, overlays, subtitles or commentary, keep each of those distinct from the visible action. "
                   "A still image can help you find a moment again, but it cannot establish the order or duration of what happens around it. "
                   "When comparing reference images, check whether their backgrounds and viewpoints are consistent; do not assume they show consecutive moments. "
                   "A useful account of the sequence names what is directly visible, notes when in the source it appears, and leaves uncertain details unresolved.")
    s2_content += ("\nFor a careful review, write down observations separately from interpretations. An observation might be that the camera changes position or that a figure enters the frame; "
                   "an interpretation would assign a reason for that movement. The latter needs more evidence than a single image or a title. "
                   "Audio can add context, but speech should be attributed only when the speaker can actually be identified from the source. "
                   "Likewise, a subtitle or caption is not a substitute for independently checking what can be heard. "
                   "Consider what the camera does not show: events before recording began, activity beyond the edges of the frame, and what followed after it stopped. "
                   "Those limits matter most when a short extract is presented as though it settles an entire story. "
                   "If you share a conclusion, cite the relevant passage in the embedded recording and explain which part remains uncertain. "
                   "That approach makes the full-length source useful even when no separate reporting, transcript or corroboration is available.")

    try:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": ENGLISH_INSTRUCTION + " Respond with valid JSON only."},
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
            required = ("lead_paragraph", "section_1_title", "section_1_content",
                        "section_2_title", "section_2_content")
            if any(not isinstance(d.get(key), str) or not d[key].strip() for key in required):
                raise ValueError("Incomplete article response")
            for key in (*required, "seo_title"):
                assert_english(d.get(key, ""), key)
            if len(re.findall(r"\b[A-Za-z]+\b", " ".join(d[key] for key in required))) < 600:
                raise ValueError("Article response below 600-word gate")
            seo_title = d.get("seo_title") if isinstance(d.get("seo_title"), str) and d["seo_title"].strip() else seo_title
            lead, s1_title, s1_content, s2_title, s2_content = (d[key] for key in required)
    except Exception as exc:
        logger.warning("LLM deep article generation failed: %s", _safe_text_llm_error(exc))

    if len(re.findall(r"\b[A-Za-z]+\b", " ".join((lead, s1_title, s1_content, s2_title, s2_content)))) < 600:
        raise WebsiteServiceError("Article below 600-word gate; CMS publish blocked")

    safe_title = html.escape(str(title))
    summary = str(source_summary or "").strip()
    summary = summary[:1800] if summary else (
        f"The available source is the complete recording titled {title}. "
        "No verified transcript or detailed source description was provided with this clip. "
        "Watch the embedded original recording to check the sequence, context and outcome directly."
    )
    safe_summary = html.escape(summary)
    safe_lead = html.escape(str(lead))
    safe_s1_title = html.escape(str(s1_title))
    safe_s1_content = html.escape(str(s1_content)).replace(chr(10), '<br><br>')
    safe_s2_title = html.escape(str(s2_title))
    safe_s2_content = html.escape(str(s2_content)).replace(chr(10), '<br><br>')
    body_html = f"""
    <div class="article-content" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.8; color: #1e293b; max-width: 820px; margin: 0 auto; font-size: 16px;">
      
      {hero_top_html}

      <section class="original-video-summary"><h2>Original video summary</h2><p>{safe_summary}</p></section>

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

    # CMS ad placement can count words between paragraphs reliably.
    from src.article_format import paragraph_html
    body_html = re.sub(r'<p\b([^>]*)>(.*?)</p>', lambda match: paragraph_html(
        html.unescape(re.sub(r'<[^>]+>', ' ', match.group(2)))), body_html, flags=re.S | re.I)
    return seo_title, body_html

def generate_curiosity_comment_with_llm(video_title: str, article_url: str, enable_llm: bool = True, profile_id: str = "") -> str:
    """
    Sinh First Comment gây tò mò (Curiosity Gap) bằng AI LLM (Gemini-3-Flash) dẫn link web.
    Fallback về mẫu chuẩn cố định nếu tắt LLM hoặc lỗi mạng.
    """
    from src.first_comment_profiles import load_profile_store, profile_first_comment
    from multi_pc.data_root import canonical_data_root
    profile_store = load_profile_store(canonical_data_root() / "data" / "first_comment_profiles.json")
    fallback_comment = profile_first_comment(video_title, article_url, profile_id, profile_store)

    if not enable_llm:
        return fallback_comment

    llm_cfg = get_llm_config()
    api_base = str(llm_cfg.get("api_base") or "").strip()
    api_key = str(llm_cfg.get("api_key") or "").strip()
    model = get_task_model("first_comment", llm_cfg)
    # A task-specific model can be retired while the configured main model is
    # still healthy. Try the main route before dropping to a template so a green
    # LLM configuration does not silently produce an opaque provider notice.
    main_model = str(llm_cfg.get("model") or "").strip()
    candidate_models = list(dict.fromkeys(item for item in (model, main_model) if item))

    prompt = f"""You are a master social media growth marketer. Write ONE viral, high-CTR First Comment in English for a Facebook Reel titled: "{video_title}".
Rules:
1. Create an intense Curiosity Gap hook about the full uncut scene, key revelation, or dramatic turnaround.
2. Must naturally incorporate this exact article link: {article_url}
3. End with a clear call-to-action to scroll down the article page to stream the full video player.
4. Keep it under 260 characters total, use 2-3 engaging emojis.
5. Return ONLY the comment text. No commentary, no quotation marks."""

    for candidate_model in candidate_models:
        try:
            payload = {
                "model": candidate_model,
                "messages": [
                    {"role": "system", "content": ENGLISH_INSTRUCTION + " Return only the final comment text."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 120,
                "temperature": 0.8
            }
            resp = _text_chat_request(api_base, api_key, candidate_model, payload, 45)
            if chat_model_unavailable(resp):
                logger.warning("First Comment model unavailable; trying the main text model")
                continue
            comment = chat_text_from_response(resp).strip()
            if not comment:
                raise ValueError("LLM comment response is empty")
            assert_english(comment, "First Comment")
            if comment.count(article_url) > 1:
                return fallback_comment
            if comment.startswith('"') and comment.endswith('"'):
                comment = comment[1:-1].strip()
            if comment.count(article_url) == 0:
                comment += f"\n👉 Full uncut video: {article_url}"
            # Facebook accepts longer comments, but keeping this compact gives
            # the requested high-CTR first-comment format.
            if len(comment) > 500:
                comment = comment[:500].rsplit(" ", 1)[0]
                if article_url not in comment:
                    comment = f"🔥 Full uncut story and video: {article_url}"
            return comment
        except Exception as exc:
            logger.warning("LLM comment gen exception (trying next model/fallback): %s", _safe_text_llm_error(exc))

    return fallback_comment

def repair_existing_website_article(article_url, clip_filename, *, content_factory, asset_metadata=None,
                                    mode="auto", progress=None):
    """Repair/revalidate the existing CMS ID while retaining its source media."""
    progress = progress or (lambda stage: None)
    metadata = asset_metadata if asset_metadata is not None else {}
    _cfg, config_file = get_website_config()
    service = WebsiteArticleService(str(config_file))
    progress("checking_existing_article")
    article = service.read_existing_article(article_url)
    source = get_clip_metadata(clip_filename)
    youtube_id = (extract_youtube_video_id(metadata.get("youtube_id")) or
                  extract_youtube_video_id(metadata.get("video_url")) or
                  extract_youtube_video_id(source.get("youtube_id")) or
                  extract_youtube_video_id(source.get("youtube_url")))
    old_body = str(article.get("description") or "")
    if not youtube_id:
        match = re.search(r'youtube(?:-nocookie)?\.com/embed/([A-Za-z0-9_-]{11})', old_body)
        youtube_id = match.group(1) if match else ""
    stream_url = str(metadata.get("website_video_url") or "") if not youtube_id else ""
    if not youtube_id and not stream_url:
        raise WebsiteServiceError("Bài Website hiện tại thiếu video gốc để xác minh; giữ URL và sửa embed trước.")
    # Validate the source on the existing page before either reusing or updating.
    service.verify_article_embed(article_url, youtube_id=youtube_id, video_stream_url=stream_url)
    source.update(article_title=article.get("title") or source.get("video_title") or "Original Video",
                  youtube_id=youtube_id, youtube_url=f"https://www.youtube.com/watch?v={youtube_id}" if youtube_id else "")
    cached = metadata.get("result") or {}
    from src.english_text import package_is_english
    try:
        from src.english_text import assert_english_title
        assert_english_title(str(article.get("title") or ""), "CMS title")
        assert_english(old_body, "CMS article")
        needs_repair = False
    except ValueError:
        needs_repair = True
    from core.article_quality import article_quality
    try:
        article_quality(old_body, minimum_words=600, minimum_images=3)
        quality_repair = False
    except WebsiteServiceError:
        quality_repair = True
    rewrite_article = needs_repair or bool(metadata.get("regenerate_text")) or quality_repair
    if rewrite_article or not package_is_english(cached) or not cached.get("article_html"):
        progress("generating_text")
        source["description"] = _source_video_summary(source, source["article_title"])
        generated = content_factory(article_url, source)
        assert_english_package(generated)
    else:
        generated = cached
    if rewrite_article:
        # Retain whole player elements and each image, including source/poster
        # URLs. Only accessible labels and article text are translated.
        media = re.findall(r'<iframe\b[^>]*>.*?</iframe\s*>|<video\b[^>]*>.*?</video\s*>|<img\b[^>]*>|<source\b[^>]*>',
                           old_body, re.I | re.S)
        title = str(generated.get("hero_title") or "Original Video")
        safe_title = html.escape(title, quote=True)
        media = [re.sub(r'\b(alt|title)\s*=\s*(["\']).*?\2',
                        lambda m: f'{m.group(1)}="{safe_title}"', tag, flags=re.I | re.S) for tag in media]
        media = [re.sub(r'(<video\b[^>]*>)(.*?)(</video\s*>)',
                        lambda m: m.group(1) + "".join(re.findall(r'<source\b[^>]*>', m.group(2), re.I)) +
                        "Your browser does not support embedded video." + m.group(3), tag, flags=re.I | re.S) for tag in media]
        image_urls = [html.unescape(url) for url in re.findall(
            r'<img\b[^>]*\bsrc=["\']([^"\']+)["\']', old_body, re.I)]
        reuse_images = len(set(image_urls[:3])) == 3
        if reuse_images:
            hero, body_images = image_urls[0], image_urls[1:3]
            metadata.setdefault("image_source", "existing_article")
        else:
            progress("repairing_images")
            hero, body_images = extract_and_upload_article_assets(
                clip_filename, title, mode=mode, metadata=metadata)
        generated["required_llm"] = False
        generated["image_source"] = metadata.get("image_source", "existing_article")
        title, body = render_content_package_article(title, hero, body_images, package=generated,
            youtube_id=youtube_id, video_stream_url=stream_url, source_summary=source.get("description", ""))
        # Keep existing player URLs/attributes, while using the standard layout.
        players = [tag for tag in media if re.match(r'<(?:iframe|video)\b', tag, re.I)]
        if players:
            body = re.sub(r'<iframe\b[^>]*>.*?</iframe\s*>|<video\b[^>]*>.*?</video\s*>',
                          lambda _: "\n".join(players), body, count=1, flags=re.I | re.S)
        extras = image_urls[3:] if reuse_images else image_urls
        if extras:
            extra_html = "".join(f'<figure><img src="{html.escape(url, quote=True)}" alt="{safe_title}" loading="lazy"></figure>' for url in extras)
            body = body.replace('<section id="full-video"', extra_html + '<section id="full-video"', 1)
        metadata.update(hero_image_url=hero, body_image_urls=body_images)
        progress("repairing_article")
        service.update_existing_article(article_url, title=title, body_html=body, expected_article=article,
                                        allow_added_images=not reuse_images,
                                        image_url=hero if not reuse_images else None)
    progress("verifying_article")
    service.verify_article(article_url)
    service.verify_article_english(article_url)
    service.verify_article_embed(article_url, youtube_id=youtube_id, video_stream_url=stream_url)
    service.verify_article_quality(article_url, minimum_words=600, minimum_images=3)
    metadata.update(result=generated, youtube_id=youtube_id, video_url=source.get("youtube_url") or metadata.get("video_url", ""),
                    website_video_status="youtube_embed_verified" if youtube_id else "verified",
                    website_video_source="youtube" if youtube_id else "original",
                    website_video_url=source.get("youtube_url") or stream_url, embed_status="ready")
    from datetime import datetime
    metadata["website_repair_verified_at"] = datetime.now().isoformat(timespec="seconds")
    metadata.pop("repair_existing_article", None)
    metadata.pop("regenerate_text", None)
    return article_url, str(metadata.get("hero_image_url") or article.get("image") or "")


def publish_clip_to_website_cms(clip_filename: str, video_title: str = None, *, content_factory=None,
                              mode="auto", progress=None, asset_metadata=None) -> tuple:
    """
    Tự động:
    1. Nhúng VIDEO GỐC bằng YouTube iframe; chỉ upload MP4 khi job cũ không có YouTube ID
    2. Tạo ảnh HOOK AI bằng LLM (gemini-3.1-flash-image) chuẩn hình mẫu boss gửi (chữ 3D đỏ to, banner vàng, vòng tròn đỏ, icon REC) và upload CDN
    3. ĐẶT ẢNH HOOK NGAY ĐẦU BÀI VIẾT và làm Thumbnail đại diện bài viết (og:image)
    4. Viết bài chuyên sâu 500+ từ, đặt YouTube embed hoặc MP4 fallback ở cuối bài
    5. Đăng bài lên CMS với slug & title 100% sạch, KHÔNG BAO GIỜ dính chữ "Clip 1", "Clip 2" hay mã job.
    Trả về: (article_url, hero_image_url)
    """
    from concurrent.futures import ThreadPoolExecutor
    progress = progress or (lambda stage: None)
    asset_metadata = asset_metadata if asset_metadata is not None else {}
    progress("checking_source")
    cfg_data, cfg_file = get_website_config()
    if not HAS_WEBSITE_SVC:
        raise WebsiteServiceError("Bản cài thiếu WebsiteArticleService")
    if not cfg_file.exists():
        raise WebsiteServiceError("Chưa cấu hình Website CMS")
    base_url = cfg_data.get("base_url", "https://bestnews.cfx.bz").rstrip("/")

    # 1. Metadata chuẩn sạch, loại bỏ hoàn toàn 'Clip 1', 'Clip 2'
    meta = get_clip_metadata(clip_filename)
    if not (extract_youtube_video_id(meta.get("youtube_id")) or extract_youtube_video_id(meta.get("youtube_url"))) and extract_youtube_video_id(asset_metadata.get("video_url")):
        meta["youtube_url"] = asset_metadata["video_url"]
        meta["youtube_id"] = extract_youtube_video_id(meta["youtube_url"])
    if not video_title or re.search(r'^(video highlight|job_\d+|clip_\d+)', video_title, re.IGNORECASE):
        video_title = meta.get("video_title") or meta.get("clean_title")
    meta["article_title"] = video_title
    meta["description"] = _source_video_summary(meta, video_title)

    # 2. Ưu tiên nhúng YouTube gốc để không lưu MP4 trên server. Chỉ upload
    # video dài làm fallback cho các job cũ không có nguồn YouTube hợp lệ.
    youtube_id = extract_youtube_video_id(meta.get("youtube_id")) or extract_youtube_video_id(meta.get("youtube_url"))
    video_stream_url = ""
    if not youtube_id:
        video_stream_url = upload_long_video_to_public_stream(meta, clip_filename)
        if not video_stream_url:
            raise WebsiteServiceError("Không có YouTube ID và upload video không trả public URL")

    if youtube_id:
        asset_metadata.update({"website_video_status": "youtube_embed_verified",
                               "website_video_url": f"https://www.youtube.com/watch?v={youtube_id}",
                               "website_video_source": "youtube"})
    else:
        asset_metadata.update({"website_video_status": "verified", "website_video_url": video_stream_url,
                               "website_video_source": "original"})

    # 3. Tạo slug ổn định cho cùng một clip qua các lần khởi động.
    clean_slug = re.sub(r'[^a-zA-Z0-9]+', '-', video_title.lower()).strip('-')[:50]
    clean_slug = re.sub(r'^(clip-\d+|job-\d+)-?', '', clean_slug).strip('-')
    if not clean_slug or len(clean_slug) < 5:
        clean_slug = "shocking-encounter-uncut-breakdown"
    clip_key = Path(str(clip_filename)).name.casefold()
    slug = f"{clean_slug}-{hashlib.sha256(clip_key.encode('utf-8')).hexdigest()[:12]}"

    # A lost CMS response is ambiguous. Before POST, look up the stable URL;
    # if it already holds this video's embed, use it instead of making a copy.
    expected_url = f"{base_url}/blog/{slug}"
    progress("checking_existing_article")
    try:
        existing = requests.get(expected_url, timeout=15)
    except requests.RequestException as exc:
        raise WebsiteServiceError(f"CMS article lookup failed; retry only after checking the existing article: {type(exc).__name__}") from exc
    if existing.status_code == 200 and urlparse(existing.url).path.rstrip("/") == urlparse(expected_url).path.rstrip("/"):
        marker = (f"youtube-nocookie.com/embed/{youtube_id}" if youtube_id else video_stream_url)
        if not marker or marker not in existing.text:
            raise WebsiteServiceError("CMS slug already exists with a different or missing video embed")
        asset_metadata.update(article_url=expected_url, repair_existing_article=True)
        progress("verifying_existing_article")
        try:
            # A matching embed alone cannot make a legacy foreign article reusable.
            from src.english_text import assert_english
            article = re.search(r"<article\b[^>]*>(.*?)</article>", existing.text, re.S | re.I)
            public = article.group(1) if article else existing.text
            public = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", "", public, flags=re.S | re.I)
            assert_english(public, "Existing CMS article")
        except ValueError as exc:
            if content_factory is None:
                from src.content_packages import generate_package
                content_factory = lambda url, metadata: generate_package(
                    video_title, metadata.get("description", ""), metadata.get("youtube_url", ""), mode=mode, article_url=url)
            return repair_existing_website_article(expected_url, clip_filename, content_factory=content_factory,
                                                   asset_metadata=asset_metadata, mode=mode, progress=progress)
        existing_service = WebsiteArticleService(str(cfg_file))
        asset_metadata.update(article_url=expected_url, repair_existing_article=True)
        progress("verifying_existing_article")
        try:
            existing_service.verify_article_english(expected_url)
            existing_service.verify_article_quality(expected_url, minimum_words=600, minimum_images=3)
        except WebsiteServiceError:
            if content_factory is None:
                from src.content_packages import generate_package
                content_factory = lambda url, metadata: generate_package(
                    video_title, metadata.get("description", ""), metadata.get("youtube_url", ""), mode=mode, article_url=url)
            return repair_existing_website_article(expected_url, clip_filename, content_factory=content_factory,
                                                   asset_metadata=asset_metadata, mode=mode, progress=progress)
        existing_service.verify_article_embed(expected_url, youtube_id=youtube_id, video_stream_url=video_stream_url)
        asset_metadata.pop("repair_existing_article", None)
        return expected_url, ""
    if existing.status_code != 404 and (existing.status_code != 200 or urlparse(existing.url).path.rstrip("/") != urlparse(base_url).path.rstrip("/")):
        raise WebsiteServiceError(f"CMS article lookup HTTP {existing.status_code}; publication paused to avoid duplicates")

    # Generate one package while extracting/uploading its images. The same
    # article_html is persisted in Content Studio and rendered into the CMS.
    if content_factory is None:
        from src.content_packages import generate_package
        content_factory = lambda url, metadata: generate_package(
            video_title, metadata.get("description", ""), metadata.get("youtube_url", ""), mode=mode, article_url=url)
    progress("generating_text_and_images")
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="article-assets") as pool:
        text_future = pool.submit(content_factory, expected_url, meta)
        assets_future = pool.submit(extract_and_upload_article_assets, clip_filename, video_title,
                                    mode=mode, metadata=asset_metadata)
        package = text_future.result()
        hero_img, body_imgs = assets_future.result()
    package["required_llm"] = False
    package["image_source"] = asset_metadata.get("image_source", "source_frame")
    if len({url for url in [hero_img, *body_imgs] if str(url).strip()}) < 3:
        raise WebsiteServiceError("Article requires three distinct source images before CMS publication")
    seo_title, body_html = generate_deep_article_content(
        video_title, hero_img, body_imgs, video_stream_url=video_stream_url, youtube_id=youtube_id,
        source_summary=meta.get("description") or _source_video_summary({"clip_filename": clip_filename}, video_title),
        prepared_package=package,
    )

    # 6. Publish lên CMS qua WebsiteArticleService kèm Hero Image (Hook Thumbnail)
    svc = WebsiteArticleService(str(cfg_file))
    progress("publishing_article")
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
    asset_metadata["article_url"] = article_url
    asset_metadata["repair_existing_article"] = True
    # Persist the URL before readback: a verification/rate-limit failure must
    # resume this article rather than generate a second CMS publication.
    progress("verifying_article")
    svc.verify_article_english(article_url)
    progress("verifying_article")
    svc.verify_article(article_url)
    svc.verify_article_embed(article_url, youtube_id=youtube_id, video_stream_url=video_stream_url)
    svc.verify_article_quality(article_url, minimum_words=600, minimum_images=3,
                               expected_images=[hero_img, *body_imgs[:2]])
    asset_metadata.update(result=package, hero_image_url=hero_img, body_image_urls=body_imgs[:2], embed_status="ready")
    asset_metadata.pop("repair_existing_article", None)

    return article_url, hero_img
