import os
import sys
import json
import re
import time
import subprocess
import uuid
import threading
import math
from contextlib import contextmanager
from functools import lru_cache

# Hide console window on Windows
NO_WINDOW = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
from pathlib import Path
import requests
from src.llm_response import json_from_chat_response

# Expose CUDA/cuDNN DLLs to Python for faster-whisper on Windows
if os.name == "nt":
    import site
    packages = site.getsitepackages()
    extra_paths = []
    for p in packages:
        for sub in ["cublas", "cudnn", "cuda_nvrtc"]:
            dll_dir = Path(p) / "nvidia" / sub / "bin"
            if dll_dir.exists():
                extra_paths.append(str(dll_dir))
    if extra_paths:
        os.environ["PATH"] = ";".join(extra_paths) + ";" + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            for ep in extra_paths:
                try:
                    os.add_dll_directory(ep)
                except Exception:
                    pass

BASE_DIR = Path(__file__).resolve().parent.parent
BIN_DIR = BASE_DIR / "bin"
DOWNLOADS_DIR = BASE_DIR / "downloads"
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"
CONFIG_DIR = BASE_DIR / "config"

# Portable bin priority: Node, yt-dlp, FFmpeg bundled beside this application.
if BIN_DIR.exists():
    os.environ["PATH"] = str(BIN_DIR) + ";" + os.environ.get("PATH", "")

YT_DLP_BIN = str(BIN_DIR / "yt-dlp.exe") if (BIN_DIR / "yt-dlp.exe").exists() else "yt-dlp"
NODE_BIN = str(BIN_DIR / "node.exe") if (BIN_DIR / "node.exe").exists() else None
COOKIES_FILE = CONFIG_DIR / "cookies.txt"
LOCAL_WHISPER_MODEL = BASE_DIR / "models" / "faster-whisper-small"
ENCODER_CODECS = {"nvenc": "h264_nvenc", "qsv": "h264_qsv", "amf": "h264_amf", "cpu": "libx264"}

def _load_render_profile():
    profile_path = BASE_DIR / "data" / "hardware_profile.json"
    try:
        payload = json.loads(profile_path.read_text(encoding="utf-8"))
        profile = payload.get("profile") if isinstance(payload, dict) else {}
        return profile if isinstance(profile, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


_RENDER_PROFILE = _load_render_profile()
_PROFILE_ENCODER = str(_RENDER_PROFILE.get("encoder") or "").lower()
_PROFILE_CONCURRENCY = int(_RENDER_PROFILE.get("max_concurrent_renders") or _RENDER_PROFILE.get("concurrency") or 1)
try:
    _PROFILE_CONCURRENCY = max(1, min(4, _PROFILE_CONCURRENCY))
except (TypeError, ValueError):
    _PROFILE_CONCURRENCY = 1
try:
    RENDER_CONCURRENCY = max(1, min(4, int(os.environ.get("HIGHLIGHT_MAX_CONCURRENT_RENDERS", str(_PROFILE_CONCURRENCY)))))
except (TypeError, ValueError):
    RENDER_CONCURRENCY = 1
RENDER_SEMAPHORE = threading.BoundedSemaphore(RENDER_CONCURRENCY)


@contextmanager
def render_slot():
    RENDER_SEMAPHORE.acquire()
    try:
        yield
    finally:
        RENDER_SEMAPHORE.release()


def get_whisper_model_source():
    """Prefer the installer-bundled model and fall back to the public model id."""
    required = ("config.json", "model.bin", "tokenizer.json")
    if LOCAL_WHISPER_MODEL.exists() and all((LOCAL_WHISPER_MODEL / name).exists() for name in required):
        return str(LOCAL_WHISPER_MODEL)
    return "small"


_WHISPER_CUDA_FAILED = False


def _whisper_device():
    """Choose CUDA only when CTranslate2 can actually see a CUDA device."""
    if _WHISPER_CUDA_FAILED:
        return "cpu", "int8"
    try:
        import ctranslate2
        if int(ctranslate2.get_cuda_device_count()) > 0:
            return "cuda", "float16"
    except Exception as exc:
        print(f"[Whisper] CUDA unavailable; using CPU int8: {exc}")
    return "cpu", "int8"


@lru_cache(maxsize=2)
def _load_whisper_model(model_source: str, device: str, compute_type: str):
    from faster_whisper import WhisperModel
    return WhisperModel(model_source, device=device, compute_type=compute_type)


def _get_whisper_model(update_status=None):
    """Load Whisper on a verified device and fail over from CUDA to CPU."""
    global _WHISPER_CUDA_FAILED
    model_source = get_whisper_model_source()
    device, compute_type = _whisper_device()
    if update_status:
        update_status(f"Initializing Whisper {device.upper()} ({compute_type})...")
    try:
        return _load_whisper_model(model_source, device, compute_type), device, compute_type
    except Exception as exc:
        if device != "cuda":
            raise RuntimeError(f"Whisper CPU initialization failed: {exc}") from exc
        print(f"[Whisper] CUDA initialization failed; falling back to CPU int8: {exc}")
        _WHISPER_CUDA_FAILED = True
        _load_whisper_model.cache_clear()
        if update_status:
            update_status("CUDA initialization failed; switching to Whisper CPU int8...")
        try:
            return _load_whisper_model(model_source, "cpu", "int8"), "cpu", "int8"
        except Exception as cpu_exc:
            raise RuntimeError(f"Whisper failed on CUDA and CPU: {cpu_exc}") from cpu_exc


def _transcribe_whisper(audio_path, update_status=None, **options):
    from src.long_transcription import INFERENCE_LOCK
    with INFERENCE_LOCK:
        return _transcribe_whisper_once(audio_path, update_status, **options)


def _transcribe_whisper_once(audio_path, update_status=None, **options):
    """Consume lazy inference inside the CUDA guard; discard partial GPU output."""
    global _WHISPER_CUDA_FAILED
    model, device, compute_type = _get_whisper_model(update_status)

    def collect(active_model):
        segments, info = active_model.transcribe(audio_path, **options)
        output = []
        for segment in segments:
            output.append(segment)
            if update_status and len(output) % 20 == 0:
                update_status(f"Whisper đang xử lý transcript: {len(output)} đoạn...")
        return output, info

    if update_status:
        update_status(f"Đang chạy Whisper {device.upper()} ({compute_type})...")
    try:
        return collect(model)
    except Exception as exc:
        # Inference loads cuBLAS/cuDNN lazily. Audio decoding and unrelated
        # failures must still propagate without an expensive second attempt.
        backend_error = any(name in str(exc).lower() for name in
                            ("cuda", "cublas", "cudnn", "nvrtc", "cufft"))
        if device != "cuda" or not backend_error:
            raise
        _WHISPER_CUDA_FAILED = True
        _load_whisper_model.cache_clear()
        if update_status:
            update_status("Whisper CUDA không khả dụng; nhận diện lại bằng CPU int8...")
        cpu_model = _load_whisper_model(get_whisper_model_source(), "cpu", "int8")
        return collect(cpu_model)


# Load config
CONFIG_FILE = BASE_DIR / "config.json"
config = {}
if CONFIG_FILE.exists():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

LLM_BASE = str(config.get("llm", {}).get("api_base") or "").strip()
LLM_KEY = str(config.get("llm", {}).get("api_key") or "").strip()
LLM_MODEL = str(config.get("llm", {}).get("model") or "").strip()

def extract_video_id(url: str) -> str:
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:shorts\/)([0-9A-Za-z_-]{11}).*',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11}).*'
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return "video_" + str(int(time.time()))

def get_youtube_transcript(video_id: str):
    """Lấy transcript từ YouTube API siêu tốc nếu có phụ đề gốc/auto-caption"""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        yta = YouTubeTranscriptApi()
        for lang_code in [['vi'], ['en'], ['en-US', 'en-GB'], None]:
            try:
                if lang_code:
                    data = yta.fetch(video_id, languages=lang_code)
                else:
                    data = yta.fetch(video_id)
                if data:
                    return [{"start": item.start, "duration": item.duration, "text": item.text} for item in data]
            except Exception:
                continue

        try:
            t_list = yta.list(video_id)
            for t in t_list:
                data = t.fetch()
                if data:
                    return [{"start": item.start, "duration": item.duration, "text": item.text} for item in data]
        except Exception:
            pass
    except Exception as e:
        print(f"[Transcript API] Không tìm thấy transcript trực tiếp từ YouTube: {e}")
    # youtube-transcript-api is frequently blocked while yt-dlp can still read
    # the same automatic captions through the authenticated player response.
    return get_ytdlp_transcript(video_id)


def _parse_ytdlp_json3(path: Path):
    """Convert yt-dlp's JSON3 captions to the pipeline transcript format."""
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    items = []
    events = payload.get("events", [])
    for event_index, event in enumerate(events):
        segments = event.get("segs") or []
        text = "".join(str(part.get("utf8") or "") for part in segments)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue
        item = {
            "start": float(event.get("tStartMs", 0)) / 1000.0,
            "duration": max(float(event.get("dDurationMs", 0)) / 1000.0, 0.1),
            "text": text,
        }
        # JSON3 automatic captions contain per-word offsets. Preserve them;
        # a plain multi-word cue with no offsets must remain segment timing.
        if any("tOffsetMs" in part for part in segments) and all(len(str(part.get("utf8") or "").split()) <= 1 for part in segments):
            end = item["start"] + item["duration"]
            if event_index + 1 < len(events):
                next_start = float(events[event_index + 1].get("tStartMs", 0)) / 1000
                if next_start > item["start"]:
                    end = min(end, next_start)
            timed = [(str(part.get("utf8") or "").strip(), item["start"] + float(part.get("tOffsetMs", 0)) / 1000)
                     for part in segments if str(part.get("utf8") or "").strip()]
            item["words"] = [{"word": word, "start": start, "end": timed[index + 1][1] if index + 1 < len(timed) else end}
                             for index, (word, start) in enumerate(timed)]
        items.append(item)
    return items


def get_ytdlp_transcript(video_id: str):
    """Download automatic captions with the bundled yt-dlp as a fast fallback."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    prefix = TEMP_DIR / f"transcript_{video_id}"
    output_template = str(prefix) + ".%(ext)s"
    base_args = [
        YT_DLP_BIN,
        "--skip-download",
        "--write-auto-subs",
        "--sub-langs", "en-orig,en,vi",
        "--sub-format", "json3",
        "--no-playlist",
        "-o", output_template,
    ]
    if NODE_BIN and Path(NODE_BIN).exists():
        base_args.extend(["--js-runtimes", f"node:{NODE_BIN}"])
    url = f"https://www.youtube.com/watch?v={video_id}"
    attempts = [base_args + [url]]
    for cookie_spec in _chrome_cookie_specs():
        attempts.append(base_args + ["--cookies-from-browser", cookie_spec, url])
    try:
        for command in attempts:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=90,
                creationflags=NO_WINDOW,
            )
            candidates = sorted(TEMP_DIR.glob(f"transcript_{video_id}.*.json3"))
            for candidate in candidates:
                items = _parse_ytdlp_json3(candidate)
                if items:
                    return items
            if result.returncode == 0:
                break
    except Exception as exc:
        print(f"[yt-dlp captions] {exc}")
    finally:
        for candidate in TEMP_DIR.glob(f"transcript_{video_id}.*.json3"):
            try:
                candidate.unlink()
            except OSError:
                pass
    return None

CHROME_PROFILE_DIR = BASE_DIR / "chrome_profile"
CHROME_USER_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "Google" / "Chrome" / "User Data"


def _chrome_cookie_specs():
    """Return yt-dlp specs for the user's Chrome and the app-owned profile.

    yt-dlp expects the *profile directory* (for example ``.../Default``), not
    Chrome's user-data root (``.../chrome_profile``). The latter silently misses
    cookies when the login lives under Default/Profile N. The desktop app opens
    the user's real Chrome profile, so include it when using the normal runtime
    value while keeping tests that patch ``CHROME_PROFILE_DIR`` isolated.
    """
    roots = [CHROME_PROFILE_DIR]
    if CHROME_PROFILE_DIR == BASE_DIR / "chrome_profile":
        roots.append(CHROME_USER_DATA_DIR)
    specs, seen = [], set()
    for root in roots:
        if not root.is_dir():
            continue
        profiles = ["Default", "Profile 1", "Profile 2", "Profile 3"]
        try:
            local_state = json.loads((root / "Local State").read_text(encoding="utf-8"))
            cache = local_state.get("profile", {}).get("info_cache", {})
            profiles.extend(cache.keys())
        except (OSError, ValueError, TypeError, AttributeError):
            pass
        for profile in profiles:
            profile_dir = root / str(profile)
            if profile_dir in seen:
                continue
            if ((profile_dir / "Network" / "Cookies").is_file()
                    or (profile_dir / "Cookies").is_file()):
                specs.append(f"chrome:{profile_dir}")
                seen.add(profile_dir)
    return specs


def download_video_and_audio(url: str, job_id: str, update_status=None):
    from src.media_download import download
    return download(sys.modules[__name__], url, job_id, update_status)


def get_word_level_transcription(audio_path: str, start_time: float, duration: float, update_status=None):
    from src.caption_timing import transcribe_slice
    try:
        return transcribe_slice(audio_path, start_time, duration, sys.modules[__name__], update_status)
    except Exception as exc:
        if update_status:
            update_status("Speech alignment unavailable; using estimated segment timing: " + str(exc))
        return []


def format_ass_time(seconds: float) -> str:
    from src.captions import ass_time
    return ass_time(seconds)


def transcript_segments_to_words(segments, clip_start: float, clip_duration: float, *, exact_only=False):
    """Slice absolute source word times; never squeeze pre-cut words into a clip."""
    from src.captions import normalize_words
    clip_end = clip_start + clip_duration
    words = []
    for segment in segments or []:
        try:
            seg_start = float(segment.get("start", 0))
            seg_end = seg_start + max(0, float(segment.get("duration", 0)))
            text = str(segment.get("text") or "").strip()
            if not math.isfinite(seg_start) or not math.isfinite(seg_end) or not text or seg_end <= clip_start or seg_start >= clip_end:
                continue
            source_words = segment.get("words") or []
            if not source_words:
                if exact_only:
                    return []
                tokens = text.split()
                step = (seg_end - seg_start) / len(tokens)
                source_words = [{"word": token, "start": seg_start + index * step,
                                 "end": seg_start + (index + 1) * step} for index, token in enumerate(tokens)]
            for item in source_words:
                start, end = float(item["start"]), float(item["end"])
                if end > clip_start and start < clip_end:
                    words.append({"word": str(item["word"]), "start": max(0, start - clip_start),
                                  "end": min(clip_duration, end - clip_start)})
        except (ValueError, TypeError, KeyError, AttributeError):
            if exact_only:
                return []
    return normalize_words(words, clip_duration)


def generate_karaoke_ass(words, ass_path: str, style_name="hormozi_yellow", *, width=1080, height=1920):
    from src.captions import write_ass
    return write_ass(words, ass_path, style_name, width=width, height=height)

def transcribe_local_whisper(audio_path: str, update_status=None):
    """Transcribe a video with verified CUDA or a portable CPU fallback."""
    try:
        from faster_whisper import WhisperModel  # noqa: F401 - validate dependency
    except Exception as exc:
        raise RuntimeError(
            "Video không có phụ đề YouTube và bộ nhận diện giọng nói faster-whisper chưa được cài đặt."
        ) from exc
    from src.long_transcription import transcribe
    return transcribe(audio_path, sys.modules[__name__], update_status)


def _fallback_highlights(transcript_items, num_clips=3, target_length="auto", video_duration=None):
    """Build exactly the requested number of usable clips when the LLM fails or under-returns."""
    try:
        requested = max(1, min(10, int(num_clips)))
    except (TypeError, ValueError):
        requested = 3

    timeline = []
    for item in transcript_items or []:
        try:
            start = max(0.0, float(item.get("start", 0.0)))
            duration = max(0.0, float(item.get("duration", 0.0)))
            timeline.append((start, start + duration))
        except (TypeError, ValueError, AttributeError):
            continue

    video_end = max((end for _, end in timeline), default=0.0)
    if video_duration is not None:
        video_end = float(video_duration)
    clip_duration = 45.0 if target_length == "short" else 55.0
    if video_end <= 0:
        video_end = max(clip_duration, requested * (clip_duration + 15.0))

    starts = [start for start, _ in timeline]
    clips = []
    for index in range(requested):
        target = video_end * ((index + 0.5) / requested)
        if starts:
            anchor = min(starts, key=lambda value: abs(value - target))
        else:
            anchor = max(0.0, target - clip_duration / 2.0)
        start_time = max(0.0, min(anchor, max(0.0, video_end - clip_duration)))
        end_time = min(video_end, start_time + clip_duration)
        if end_time - start_time < 10.0:
            start_time = max(0.0, end_time - min(clip_duration, video_end))
        clips.append({
            "start": round(start_time, 2),
            "end": round(end_time, 2),
            "start_time": round(start_time, 2),
            "end_time": round(end_time, 2),
            "hook_title": f"Highlight phan {index + 1}",
            "title": f"Highlight phan {index + 1}",
            "summary": "Doan noi dung noi bat duoc chon tu transcript",
            "reason": "Doan noi dung noi bat duoc chon tu transcript",
            "viral_score": max(80, 92 - index),
        })
    return clips


def _ensure_highlight_count(clips, transcript_items, num_clips=3, target_length="auto", video_duration=None):
    from src.render_quality import seconds
    try:
        requested = max(1, min(10, int(num_clips)))
    except (TypeError, ValueError):
        requested = 3
    result = []
    for clip in clips or []:
        try:
            start = seconds(clip.get("start", clip.get("start_time")))
            end = seconds(clip.get("end", clip.get("end_time")))
            if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start:
                continue
            if video_duration is not None:
                if start >= video_duration:
                    continue
                end = min(end, video_duration)
            if end - start < min(15, video_duration or 15):
                continue
            result.append({**clip, "start": start, "start_time": start, "end": end, "end_time": end})
        except (TypeError, ValueError, AttributeError):
            continue
        if len(result) == requested:
            break
    if len(result) >= requested:
        return result

    candidates = _fallback_highlights(transcript_items, requested, target_length, video_duration)
    existing = {(round(float(c.get("start", 0.0)), 1), round(float(c.get("end", 0.0)), 1)) for c in result}
    for candidate in candidates:
        key = (round(candidate["start"], 1), round(candidate["end"], 1))
        if key not in existing:
            result.append(candidate)
            existing.add(key)
        if len(result) >= requested:
            break
    return result


def ask_llm_for_highlights(transcript_items, *args, num_clips=3, target_length="auto", criteria="hook_viral", hook_duration=6, update_status=None, **kwargs):
    # Support positional args if passed as (transcript_items, duration, title, num_clips)
    if len(args) >= 1 and isinstance(args[0], (int, float)):
        kwargs.setdefault("video_duration", args[0])
    if len(args) >= 2 and isinstance(args[1], str):
        # title was passed
        pass
    if len(args) >= 3 and isinstance(args[2], int):
        num_clips = args[2]
    if "num_clips" in kwargs:
        num_clips = kwargs["num_clips"]
    if "target_length" in kwargs:
        target_length = kwargs["target_length"]
    if "criteria" in kwargs:
        criteria = kwargs["criteria"]
    if "hook_duration" in kwargs:
        hook_duration = kwargs["hook_duration"]
    if "update_status" in kwargs:
        update_status = kwargs["update_status"]
    video_duration = kwargs.get("video_duration")
    if video_duration is not None:
        video_duration = float(video_duration)
        if not math.isfinite(video_duration) or video_duration <= 0:
            raise ValueError("Source video duration must be positive")
    """Gửi transcript vào LLM để phân tích và trích xuất các đoạn highlight đắt giá nhất"""
    if update_status:
        update_status(f"AI ({LLM_MODEL}) đang phân tích kịch bản tìm {num_clips} highlight...")
    
    lines = []
    for item in transcript_items:
        m, s = divmod(int(item['start']), 60)
        lines.append(f"[{float(item['start']):.2f} seconds | {m:02d}:{s:02d}] {item['text']}")
    full_text = "\n".join(lines)
    
    if len(full_text) > 35000:
        full_text = full_text[:35000] + "\n...[Nội dung tiếp tục]..."

    prompt = f"""Bạn là một chuyên gia biên tập video ngắn viral (TikTok, Reels, YouTube Shorts) hàng đầu, tương tự như thuật toán của Vizard.ai và OpusClip.
Nhiệm vụ của bạn là đọc bản ghi âm có timestamp dưới đây và chọn ra đúng {num_clips} đoạn HIGHLIGHT đắt giá nhất để cắt thành video ngắn.

TIÊU CHÍ LỌC:
- Định dạng yêu cầu: {criteria} (Tập trung vào đoạn mở đầu có Hook giật gân, cao trào, hoặc bài học sâu sắc).
- Độ dài mỗi clip: khoảng {30 if target_length=='short' else 45} đến {60 if target_length=='short' else 75} giây.
- Điểm bắt đầu (start_time): Phải là một câu nói mở đầu cuốn hút, gây tò mò kích thích cao trào ngay lập tức (trong {hook_duration} giây đầu tiên của đoạn clip).
- Điểm kết thúc (end_time): Phải là điểm kết thúc trọn vẹn một ý nghĩ hoặc câu chuyện, không bị cắt giữa chừng khi người nói chưa hết câu.
- Tính điểm viral (viral_score): từ 80 đến 99 điểm.
- Thời lượng video thật: {video_duration if video_duration is not None else 'the transcript timeline'} giây. Mọi mốc cắt phải nằm trong video này; không tạo timestamp bên ngoài video.

ĐỊNH DẠNG TRẢ VỀ: Trả về duy nhất một JSON Array hợp lệ, không giải thích gì thêm:
start_time và end_time là tổng số giây, không phải phút.giây. Ví dụ 13:08 là 788 giây, không phải 13.08.
[
  {{
    "start_time": 12.5,
    "end_time": 58.0,
    "hook_title": "Tiêu đề giật gân tiếng Việt kích thích tò mò",
    "summary": "Tóm tắt ngắn gọn nội dung clip trong 1 câu",
    "viral_score": 96
  }}
]

Dưới đây là transcript có timestamp:
{full_text}
"""
    headers = {
        "Authorization": f"Bearer {LLM_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }
    
    try:
        resp = requests.post(f"{LLM_BASE}/chat/completions", json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        clips = json_from_chat_response(resp)

        # Chuẩn hóa format keys để tương thích cả app.py và pipeline
        normalized_clips = []
        raw_list = clips if isinstance(clips, list) else [clips]
        for c in raw_list:
            from src.render_quality import seconds
            s_time = seconds(c.get("start_time", c.get("start", 0.0)))
            e_time = seconds(c.get("end_time", c.get("end", s_time + 45.0)))
            h_title = c.get("hook_title", c.get("title", "Highlight Clip"))
            c_summary = c.get("summary", c.get("reason", ""))
            v_score = int(c.get("viral_score", 88))
            normalized_clips.append({
                "start": s_time,
                "end": e_time,
                "start_time": s_time,
                "end_time": e_time,
                "title": h_title,
                "hook_title": h_title,
                "summary": c_summary,
                "reason": c_summary,
                "viral_score": v_score
            })
        return _ensure_highlight_count(normalized_clips, transcript_items, num_clips, target_length, video_duration)
    except Exception as e:
        # Desktop stdout can be a redirected legacy Windows code page. Keep the
        # original failure visible as ASCII escapes without masking the fallback.
        message = f"[LLM Error] Không trích xuất được highlight từ LLM: {e}"
        try:
            print(message.encode("ascii", errors="backslashreplace").decode("ascii"))
        except (OSError, UnicodeError, ValueError):
            pass  # An unavailable log stream must not turn LLM fallback into a failed job.
        return _fallback_highlights(transcript_items, num_clips, target_length, video_duration)

def render_highlight_clip(source_video: str = None, audio_path: str = None, start_time: float = None, end_time: float = None, output_path: str = None, aspect_ratio="9:16", reframe_mode="face_center", subtitle_style="hormozi_yellow", update_status=None, **kwargs):
    # Support kwargs from app.py: video_path, start_sec, end_sec, job_id, clip_idx, output_dir
    if source_video is None:
        source_video = kwargs.get("video_path")
    if start_time is None:
        start_time = float(kwargs.get("start_sec", 0.0))
    if end_time is None:
        end_time = float(kwargs.get("end_sec", start_time + 45.0))
    if output_path is None:
        out_dir = Path(kwargs.get("output_dir", OUTPUT_DIR))
        out_dir.mkdir(parents=True, exist_ok=True)
        j_id = kwargs.get("job_id", f"job_{int(time.time())}")
        c_idx = kwargs.get("clip_idx", 1)
        output_path = out_dir / f"{j_id}_clip_{c_idx}.mp4"
    else:
        output_path = Path(output_path)
    """Cắt, tạo phụ đề động Karaoke và render video bằng FFmpeg hardware encoder (auto)"""
    from src.media_validation import probe_video, InvalidMedia
    source_duration = probe_video(source_video)["duration"]
    start_time, end_time = float(start_time), float(end_time)
    if (not math.isfinite(start_time) or not math.isfinite(end_time) or start_time < 0
            or end_time <= start_time or start_time >= source_duration):
        raise InvalidMedia(f"Mốc cắt {start_time}–{end_time}s không hợp lệ: video gốc dài {source_duration:.2f}s.")
    end_time = min(end_time, source_duration)
    duration = end_time - start_time
        
    if update_status:
        update_status(f"Đang phân tích lời thoại và tạo phụ đề chạy chữ ({subtitle_style})...")

    # 1. Tạo phụ đề ASS Karaoke từ đoạn audio
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    ass_path = TEMP_DIR / f"{Path(output_path).stem}.{uuid.uuid4().hex}.ass"
    words = []
    if subtitle_style and subtitle_style != "none":
        segments = kwargs.get("all_segments")
        words = transcript_segments_to_words(segments, start_time, duration, exact_only=True)
        timing = kwargs.get("subtitle_timing") or "accurate"
        if not words and timing != "fast":
            words = get_word_level_transcription(source_video, start_time, duration, update_status=update_status)
        if not words:
            words = transcript_segments_to_words(segments, start_time, duration)
            if words and update_status:
                update_status("Phụ đề dùng thời gian ước lượng theo câu; chưa có timestamp từng từ từ audio.")
        if words:
            width, height = {"9:16": (1080, 1920), "1:1": (1080, 1080), "16:9": (1920, 1080)}.get(aspect_ratio, (1920, 1080))
            generate_karaoke_ass(words, str(ass_path), style_name=subtitle_style, width=width, height=height)

    if update_status:
        update_status(f"Đang render video 9:16 ({duration:.1f}s) qua GPU (auto)...")

    # 2. Xây dựng filter FFmpeg theo aspect ratio
    if aspect_ratio == "9:16":
        if reframe_mode == "blur_bg":
            vf = "split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=20[bg];[b]scale=1080:-1[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2"
        else:
            # Crop 9:16 ở giữa khung hình (1080x1920)
            vf = "scale=1080:1920:force_original_aspect_ratio=increase:force_divisible_by=2,crop=1080:1920"
    elif aspect_ratio == "1:1":
        vf = "crop=min(in_w\\,in_h):min(in_w\\,in_h),scale=1080:1080"
    else:
        vf = "scale=1920:1080:force_original_aspect_ratio=decrease"

    pipeline_cfg = config.get("video_pipeline", {}) if isinstance(config.get("video_pipeline"), dict) else {}

    # Ghép filter phụ đề ASS nếu có. Video nguồn thường đã burn caption sẵn;
    # che mờ vùng caption của nguồn để tránh hai lớp chữ chồng nhau sau khi crop 9:16.
    if words and ass_path.exists():
        if aspect_ratio == "9:16" and pipeline_cfg.get("source_caption_cleanup", True):
            # Original burned-in captions can touch the bottom edge. Cover the
            # entire remaining band before drawing our new word-timed captions.
            vf = f"{vf},drawbox=x=0:y=ih*0.70:w=iw:h=ih*0.30:color=black:t=fill"
        # Đường dẫn cho FFmpeg trên Windows cần escape dấu hai chấm và gạch chéo
        from src.captions import FONTS_DIR
        ass_str = str(ass_path).replace("\\", "/").replace(":", "\\:").replace("'", "'\\\\''")
        fonts_str = str(FONTS_DIR).replace("\\", "/").replace(":", "\\:").replace("'", "'\\\\''")
        vf = f"{vf},subtitles=filename='{ass_str}':fontsdir='{fonts_str}'"
    configured = str(pipeline_cfg.get("encoder") or "auto").lower()
    vf += ",setsar=1,setpts=PTS-STARTPTS"
    env_encoder = os.environ.get("HIGHLIGHT_ENCODER", "").lower()
    encoder = configured if configured in ENCODER_CODECS and configured != "auto" else (env_encoder or _PROFILE_ENCODER or "cpu")
    if encoder not in ENCODER_CODECS:
        encoder = "cpu"
    codec = ENCODER_CODECS[encoder]
    crf = str(pipeline_cfg.get("crf") or 21)

    def build_command(selected_encoder):
        selected_codec = ENCODER_CODECS[selected_encoder]
        command = [
            "ffmpeg", "-y", "-ss", str(start_time), "-i", str(source_video), "-t", str(duration),
            "-vf", vf, "-r", "30", "-fps_mode", "cfr", "-c:v", selected_codec,
        ]
        if selected_encoder == "cpu":
            command.extend(["-preset", "veryfast", "-crf", crf])
        elif selected_encoder == "nvenc":
            command.extend(["-preset", str(pipeline_cfg.get("nvenc_preset") or "p2"), "-cq", crf])
        elif selected_encoder == "qsv":
            command.extend(["-preset", "veryfast", "-global_quality", crf])
        else:
            command.extend(["-quality", "speed", "-qp_i", crf, "-qp_p", crf])
        command.extend(["-af", "asetpts=PTS-STARTPTS,aresample=async=1:first_pts=0",
                        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output_path)])
        return command

    if update_status:
        update_status(f"Đang render bằng {codec} (tối đa {RENDER_CONCURRENCY} render đồng thời)...")
    # Render into a private temporary name. The output watcher only sees the
    # final MP4 after ffmpeg exits successfully, so a half-written file can
    # never enter Content/LLM or the posting queue.
    final_output = Path(output_path)
    temporary_output = final_output.with_name(f".{final_output.stem}.rendering.{uuid.uuid4().hex}{final_output.suffix}")
    def command_to_temp(command):
        return command[:-1] + [str(temporary_output)]
    with render_slot():
        cmd = command_to_temp(build_command(encoder))
        rendered = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=max(900, int(duration * 120)), creationflags=NO_WINDOW)
        if rendered.returncode != 0 and encoder != "cpu":
            print(f"[FFmpeg Warning] {codec} failed; fallback to libx264: {rendered.stderr[:300]}")
            rendered = subprocess.run(command_to_temp(build_command("cpu")), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=max(900, int(duration * 180)), creationflags=NO_WINDOW)
        if rendered.returncode != 0:
            temporary_output.unlink(missing_ok=True)
            raise RuntimeError(f"FFmpeg render thất bại: {rendered.stderr}")
    try:
        from src.render_quality import validate_render
        validate_render(temporary_output, duration)
    except Exception:
        temporary_output.unlink(missing_ok=True)
        raise
    final_output.parent.mkdir(parents=True, exist_ok=True)
    os.replace(temporary_output, final_output)

    return final_output
