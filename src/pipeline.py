import os
import sys
import json
import re
import time
import subprocess
import threading
from contextlib import contextmanager

# Hide console window on Windows
NO_WINDOW = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
from pathlib import Path
import requests

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
RENDER_CONCURRENCY = max(1, int(os.environ.get("HIGHLIGHT_MAX_CONCURRENT_RENDERS", "1")))
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
    """Láº¥y transcript tá»« YouTube API siÃªu tá»‘c náº¿u cÃ³ phá»¥ Ä‘á» gá»‘c/auto-caption"""
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
        print(f"[Transcript API] KhÃ´ng tÃ¬m tháº¥y transcript trá»±c tiáº¿p tá»« YouTube: {e}")
    # youtube-transcript-api is frequently blocked while yt-dlp can still read
    # the same automatic captions through the authenticated player response.
    return get_ytdlp_transcript(video_id)


def _parse_ytdlp_json3(path: Path):
    """Convert yt-dlp's JSON3 captions to the pipeline transcript format."""
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    items = []
    for event in payload.get("events", []):
        segments = event.get("segs") or []
        text = "".join(str(part.get("utf8") or "") for part in segments)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue
        items.append({
            "start": float(event.get("tStartMs", 0)) / 1000.0,
            "duration": max(float(event.get("dDurationMs", 0)) / 1000.0, 0.1),
            "text": text,
        })
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
    if CHROME_PROFILE_DIR.exists():
        attempts.append(base_args + ["--cookies-from-browser", f"chrome:{CHROME_PROFILE_DIR}", url])
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

def download_video_and_audio(url: str, job_id: str, update_status=None):
    """
    Tải video siêu tốc bằng yt-dlp với 8 luồng song song.
    Mặc định: Tải trực tiếp siêu tốc KHÔNG dùng cookie để đạt tốc độ tối đa và không phụ thuộc trình duyệt.
    Fallback: Nếu gặp bot-check/HTTP 403, dùng Chrome profile của đúng thư mục cài hiện tại.
    """
    if update_status:
        update_status("Đang tải video siêu tốc bằng yt-dlp đa luồng (8 connections)...")
    
    out_video = DOWNLOADS_DIR / f"{job_id}.mp4"
    out_audio = TEMP_DIR / f"{job_id}.mp3"
    
    base_args = []
    if NODE_BIN and Path(NODE_BIN).exists():
        base_args.extend(["--js-runtimes", f"node:{NODE_BIN}"])

    def try_download(use_fallback=False):
        dl_args = list(base_args)
        if use_fallback:
            if CHROME_PROFILE_DIR.exists():
                dl_args.extend(["--cookies-from-browser", f"chrome:{CHROME_PROFILE_DIR}"])
            elif COOKIES_FILE.exists():
                dl_args.extend(["--cookies", str(COOKIES_FILE)])

        info_cmd = [YT_DLP_BIN, "--dump-json", "--no-warnings"] + dl_args + [url]
        info_proc = subprocess.run(info_cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", creationflags=NO_WINDOW)
        video_title = "YouTube Video"
        duration = 0
        if info_proc.returncode == 0 and info_proc.stdout:
            try:
                info = json.loads(info_proc.stdout.strip().split("\n")[0])
                video_title = info.get("title", video_title)
                duration = info.get("duration", 0)
            except Exception:
                pass

        cmd = [
            YT_DLP_BIN,
            "-N", "8",
            "--concurrent-fragments", "8",
            "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
            "--merge-output-format", "mp4",
            "-o", str(out_video),
            "--no-playlist"
        ] + dl_args + [url]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", creationflags=NO_WINDOW)
        return res, video_title, duration

    # Bước 1: Tải trực tiếp siêu tốc (Không cookies)
    res, video_title, duration = try_download(use_fallback=False)
    
    # Bước 2: Kiểm tra nếu gặp lỗi bot check hoặc 403, kích hoạt fallback Chrome Local Profile
    if res.returncode != 0 or not out_video.exists():
        err_msg = res.stderr or ""
        is_bot_check = any(k in err_msg.lower() for k in ["sign in to confirm", "bot", "403", "forbidden", "login"])
        if is_bot_check or CHROME_PROFILE_DIR.exists():
            if update_status:
                update_status(f"Kích hoạt Fallback Chrome Local: {CHROME_PROFILE_DIR}...")
            res_fb, fb_title, fb_duration = try_download(use_fallback=True)
            if res_fb.returncode == 0 and out_video.exists():
                res = res_fb
                if fb_title and fb_title != "YouTube Video":
                    video_title = fb_title
                if fb_duration:
                    duration = fb_duration
            else:
                raise RuntimeError(f"yt-dlp tải video thất bại (kể cả khi đã fallback Chrome profile): {res_fb.stderr}")
        else:
            raise RuntimeError(f"yt-dlp tải video thất bại: {res.stderr}")

    cmd_audio = [
        "ffmpeg", "-y", "-i", str(out_video),
        "-vn", "-acodec", "libmp3lame", "-ar", "16000", "-ac", "1", "-q:a", "2",
        str(out_audio)
    ]
    subprocess.run(cmd_audio, capture_output=True, creationflags=NO_WINDOW)
    
    return {
        "video_path": str(out_video),
        "audio_path": str(out_audio),
        "title": video_title,
        "duration": duration
    }

def get_word_level_transcription(audio_path: str, start_time: float, duration: float, update_status=None):
    """Cáº¯t Ä‘oáº¡n audio ngáº¯n tÆ°Æ¡ng á»©ng vá»›i clip rá»“i dÃ¹ng faster-whisper (CUDA float16) trÃ­ch xuáº¥t tá»«ng tá»« kÃ¨m timestamp"""
    try:
        from faster_whisper import WhisperModel
    except Exception:
        WhisperModel = None
    clip_audio_tmp = TEMP_DIR / f"sub_slice_{int(time.time()*1000)}.mp3"
    
    # Cáº¯t chÃ­nh xÃ¡c Ä‘oáº¡n audio ngáº¯n nÃ y Ä‘á»ƒ Whisper nháº­n diá»‡n cá»±c nhanh (chá»‰ máº¥t 1-2s trÃªn GPU)
    cmd_cut = [
        "ffmpeg", "-y",
        "-ss", str(start_time),
        "-t", str(duration),
        "-i", str(audio_path),
        "-acodec", "copy",
        str(clip_audio_tmp)
    ]
    subprocess.run(cmd_cut, capture_output=True, creationflags=NO_WINDOW)

    words = []
    try:
        try:
            model = WhisperModel(get_whisper_model_source(), device="cuda", compute_type="float16")
        except Exception as e:
            print(f"[Whisper CUDA fallback CPU]: {e}")
            model = WhisperModel(get_whisper_model_source(), device="cpu", compute_type="int8")

        segments, _ = model.transcribe(str(clip_audio_tmp), word_timestamps=True, beam_size=1)
        for s in segments:
            if s.words:
                for w in s.words:
                    word_clean = w.word.strip()
                    if word_clean:
                        words.append({
                            "word": word_clean,
                            "start": float(w.start),
                            "end": float(w.end)
                        })
    except Exception as e:
        print(f"[Whisper word transcription error]: {e}")
    finally:
        if clip_audio_tmp.exists():
            try:
                clip_audio_tmp.unlink()
            except Exception:
                pass

    return words

def format_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    cs = int((s - int(s)) * 100)
    return f"{h}:{m:02d}:{int(s):02d}.{cs:02d}"

def transcript_segments_to_words(segments, clip_start: float, clip_duration: float):
    """Create clip-relative word timing from transcript segments.

    YouTube captions already contain reliable segment timing. Reusing it avoids
    loading Whisper once for every rendered clip and guarantees subtitles on a
    clean installation whenever captions were available for highlight analysis.
    """
    clip_end = clip_start + clip_duration
    words = []
    for segment in segments or []:
        try:
            seg_start = float(segment.get("start", 0.0))
            seg_end = seg_start + max(0.0, float(segment.get("duration", 0.0)))
            text = str(segment.get("text") or "").strip()
        except (TypeError, ValueError, AttributeError):
            continue
        if not text or seg_end <= clip_start or seg_start >= clip_end:
            continue

        tokens = [token for token in re.findall(r"[^\s]+", text) if token.strip()]
        if not tokens:
            continue
        visible_start = max(seg_start, clip_start)
        visible_end = min(max(seg_end, visible_start + 0.2), clip_end)
        step = max(0.08, (visible_end - visible_start) / len(tokens))
        for index, token in enumerate(tokens):
            word_start = visible_start + index * step
            word_end = min(visible_end, word_start + step)
            words.append({
                "word": token,
                "start": max(0.0, word_start - clip_start),
                "end": max(0.1, word_end - clip_start),
            })
    return words

def generate_karaoke_ass(words, ass_path: str, style_name="hormozi_yellow"):
    """Táº¡o file phá»¥ Ä‘á» ASS vá»›i hiá»‡u á»©ng cháº¡y chá»¯ Karaoke (Hormozi style) ná»•i báº­t"""
    active_color = "&H0022FFFF&" # VÃ ng neon ná»•i báº­t
    inactive_color = "&H00FFFFFF&" # Tráº¯ng tinh
    if style_name == "clean_white":
        active_color = "&H0000FFFF&"
    elif style_name == "neon_green":
        active_color = "&H0033FF00&"

    header = f"""[Script Info]
Title: Highlight Video Karaoke
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,82,{inactive_color},&H0000FFFF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,6,3,2,60,60,300,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    if not words:
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(header)
        return ass_path

    # NhÃ³m 3-4 tá»« thÃ nh 1 cá»¥m hiá»ƒn thá»‹ (chunk) giÃºp ngÆ°á»i xem Ä‘á»c lÆ°á»›t dá»… dÃ ng
    GROUP_SIZE = 3
    lines = []
    clean_words = []
    for w in words:
        w_text = re.sub(r"[^\w'\-]", "", w["word"]).strip().upper()
        if w_text:
            clean_words.append({
                "word": w_text,
                "start": max(0.0, float(w["start"])),
                "end": max(float(w["start"]) + 0.1, float(w["end"]))
            })

    for i in range(0, len(clean_words), GROUP_SIZE):
        chunk = clean_words[i:i + GROUP_SIZE]
        if not chunk:
            continue
        for idx, active_item in enumerate(chunk):
            t_start = format_ass_time(active_item["start"])
            t_end = format_ass_time(active_item["end"])
            
            # TÃ´ mÃ u tá»« Ä‘ang nÃ³i (Active Karaoke word)
            parts = []
            for j, item in enumerate(chunk):
                if j == idx:
                    parts.append(r"{\c" + active_color + r"\b1\fscx112\fscy112}" + item["word"] + r"{\fscx100\fscy100\c" + inactive_color + r"\b0}")
                else:
                    parts.append(r"{\c" + inactive_color + r"}" + item["word"])
            full_line = " ".join(parts)
            lines.append(f"Dialogue: 0,{t_start},{t_end},Default,,0,0,0,,{full_line}")

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(lines) + "\n")
    return ass_path

def transcribe_local_whisper(audio_path: str, update_status=None):
    """Nháº­n diá»‡n toÃ n bá»™ video khi khÃ´ng cÃ³ phá»¥ Ä‘á» sáºµn"""
    if update_status:
        update_status("Äang nháº­n diá»‡n giá»ng nÃ³i báº±ng GPU NVIDIA (CUDA float16)...")
    try:
        from faster_whisper import WhisperModel
    except Exception as exc:
        raise RuntimeError(
            "Video không có phụ đề YouTube và bộ nhận diện giọng nói faster-whisper chưa được cài đặt."
        ) from exc
    try:
        model = WhisperModel(get_whisper_model_source(), device="cuda", compute_type="float16")
    except Exception as e:
        print(f"[Whisper] CUDA khÃ´ng kháº£ dá»¥ng, dÃ¹ng CPU: {e}")
        model = WhisperModel(get_whisper_model_source(), device="cpu", compute_type="int8")

    segments, info = model.transcribe(audio_path, beam_size=1)
    results = []
    for s in segments:
        results.append({
            "start": s.start,
            "duration": s.end - s.start,
            "text": s.text.strip()
        })
    return results

def _fallback_highlights(transcript_items, num_clips=3, target_length="auto"):
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


def _ensure_highlight_count(clips, transcript_items, num_clips=3, target_length="auto"):
    try:
        requested = max(1, min(10, int(num_clips)))
    except (TypeError, ValueError):
        requested = 3
    result = list(clips or [])[:requested]
    if len(result) >= requested:
        return result

    candidates = _fallback_highlights(transcript_items, requested, target_length)
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
        # duration was passed
        pass
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
    """Gá»­i transcript vÃ o LLM Ä‘á»ƒ phÃ¢n tÃ­ch vÃ  trÃ­ch xuáº¥t cÃ¡c Ä‘oáº¡n highlight Ä‘áº¯t giÃ¡ nháº¥t"""
    if update_status:
        update_status(f"AI ({LLM_MODEL}) Ä‘ang phÃ¢n tÃ­ch ká»‹ch báº£n tÃ¬m {num_clips} highlight...")
    
    lines = []
    for item in transcript_items:
        m, s = divmod(int(item['start']), 60)
        lines.append(f"[{m:02d}:{s:02d}] {item['text']}")
    full_text = "\n".join(lines)
    
    if len(full_text) > 35000:
        full_text = full_text[:35000] + "\n...[Ná»™i dung tiáº¿p tá»¥c]..."

    prompt = f"""Báº¡n lÃ  má»™t chuyÃªn gia biÃªn táº­p video ngáº¯n viral (TikTok, Reels, YouTube Shorts) hÃ ng Ä‘áº§u, tÆ°Æ¡ng tá»± nhÆ° thuáº­t toÃ¡n cá»§a Vizard.ai vÃ  OpusClip.
Nhiá»‡m vá»¥ cá»§a báº¡n lÃ  Ä‘á»c báº£n ghi Ã¢m cÃ³ timestamp dÆ°á»›i Ä‘Ã¢y vÃ  chá»n ra Ä‘Ãºng {num_clips} Ä‘oáº¡n HIGHLIGHT Ä‘áº¯t giÃ¡ nháº¥t Ä‘á»ƒ cáº¯t thÃ nh video ngáº¯n.

TIÃŠU CHÃ Lá»ŒC:
- Äá»‹nh dáº¡ng yÃªu cáº§u: {criteria} (Táº­p trung vÃ o Ä‘oáº¡n má»Ÿ Ä‘áº§u cÃ³ Hook giáº­t gÃ¢n, cao trÃ o, hoáº·c bÃ i há»c sÃ¢u sáº¯c).
- Äá»™ dÃ i má»—i clip: khoáº£ng {30 if target_length=='short' else 45} Ä‘áº¿n {60 if target_length=='short' else 75} giÃ¢y.
- Äiá»ƒm báº¯t Ä‘áº§u (start_time): Pháº£i lÃ  má»™t cÃ¢u nÃ³i má»Ÿ Ä‘áº§u cuá»‘n hÃºt, gÃ¢y tÃ² mÃ² kÃ­ch thÃ­ch cao trÃ o ngay láº­p tá»©c (trong {hook_duration} giÃ¢y Ä‘áº§u tiÃªn cá»§a Ä‘oáº¡n clip).
- Äiá»ƒm káº¿t thÃºc (end_time): Pháº£i lÃ  Ä‘iá»ƒm káº¿t thÃºc trá»n váº¹n má»™t Ã½ nghÄ© hoáº·c cÃ¢u chuyá»‡n, khÃ´ng bá»‹ cáº¯t giá»¯a chá»«ng khi ngÆ°á»i nÃ³i chÆ°a háº¿t cÃ¢u.
- TÃ­nh Ä‘iá»ƒm viral (viral_score): tá»« 80 Ä‘áº¿n 99 Ä‘iá»ƒm.

Äá»ŠNH Dáº NG TRáº¢ Vá»€: Tráº£ vá» duy nháº¥t má»™t JSON Array há»£p lá»‡, khÃ´ng giáº£i thÃ­ch gÃ¬ thÃªm:
[
  {{
    "start_time": 12.5,
    "end_time": 58.0,
    "hook_title": "TiÃªu Ä‘á» giáº­t gÃ¢n tiáº¿ng Viá»‡t kÃ­ch thÃ­ch tÃ² mÃ²",
    "summary": "TÃ³m táº¯t ngáº¯n gá»n ná»™i dung clip trong 1 cÃ¢u",
    "viral_score": 96
  }}
]

DÆ°á»›i Ä‘Ã¢y lÃ  transcript cÃ³ timestamp:
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
        res_data = resp.json()
        content = res_data["choices"][0]["message"]["content"]
        
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            clips = json.loads(json_match.group(0))
        else:
            clips = json.loads(content)

        # Chuáº©n hÃ³a format keys Ä‘á»ƒ tÆ°Æ¡ng thÃ­ch cáº£ app.py vÃ  pipeline
        normalized_clips = []
        raw_list = clips if isinstance(clips, list) else [clips]
        for c in raw_list:
            s_time = float(c.get("start_time", c.get("start", 0.0)))
            e_time = float(c.get("end_time", c.get("end", s_time + 45.0)))
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
        return _ensure_highlight_count(normalized_clips, transcript_items, num_clips, target_length)
    except Exception as e:
        print(f"[LLM Error] KhÃ´ng trÃ­ch xuáº¥t Ä‘Æ°á»£c highlight tá»« LLM: {e}")
        return _fallback_highlights(transcript_items, num_clips, target_length)

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
    """Cáº¯t, táº¡o phá»¥ Ä‘á» Ä‘á»™ng Karaoke vÃ  render video báº±ng FFmpeg hardware encoder (auto)"""
    duration = end_time - start_time
    if duration <= 0:
        duration = 30
        
    if update_status:
        update_status(f"Äang phÃ¢n tÃ­ch lá»i thoáº¡i vÃ  táº¡o phá»¥ Ä‘á» cháº¡y chá»¯ ({subtitle_style})...")

    # 1. Táº¡o phá»¥ Ä‘á» ASS Karaoke tá»« Ä‘oáº¡n audio
    ass_path = TEMP_DIR / f"{Path(output_path).stem}.ass"
    words = []
    if subtitle_style and subtitle_style != "none":
        words = transcript_segments_to_words(kwargs.get("all_segments"), start_time, duration)
        if not words and audio_path and Path(audio_path).exists():
            words = get_word_level_transcription(audio_path, start_time, duration, update_status=update_status)
        if words:
            generate_karaoke_ass(words, str(ass_path), style_name=subtitle_style)

    if update_status:
        update_status(f"Äang render video 9:16 ({duration:.1f}s) qua GPU (auto)...")

    # 2. XÃ¢y dá»±ng filter FFmpeg theo aspect ratio
    if aspect_ratio == "9:16":
        if reframe_mode == "blur_bg":
            vf = "split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=20[bg];[b]scale=1080:-1[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2"
        else:
            # Crop 9:16 á»Ÿ giá»¯a khung hÃ¬nh (1080x1920)
            vf = "scale=-1:1920,crop=1080:1920:(in_w-1080)/2:0"
    elif aspect_ratio == "1:1":
        vf = "crop=min(in_w\\,in_h):min(in_w\\,in_h),scale=1080:1080"
    else:
        vf = "scale=1920:1080:force_original_aspect_ratio=decrease"

    pipeline_cfg = config.get("video_pipeline", {}) if isinstance(config.get("video_pipeline"), dict) else {}

    # GhÃ©p filter phá»¥ Ä‘á» ASS náº¿u cÃ³. Video nguá»“n thÆ°á»ng Ä‘Ã£ burn caption sáºµn;
    # che má» vÃ¹ng caption cá»§a nguá»“n Ä‘á»ƒ trÃ¡nh hai lá»›p chá»¯ chá»“ng nhau sau khi crop 9:16.
    if ass_path.exists() and ass_path.stat().st_size > 300:
        if aspect_ratio == "9:16" and pipeline_cfg.get("source_caption_cleanup", True):
            vf = f"{vf},drawbox=x=0:y=ih*0.70:w=iw:h=ih*0.22:color=black@0.90:t=fill"
        # ÄÆ°á»ng dáº«n cho FFmpeg trÃªn Windows cáº§n escape dáº¥u hai cháº¥m vÃ  gáº¡ch chÃ©o
        ass_str = str(ass_path).replace("\\", "/").replace(":", "\\:")
        vf = f"{vf},subtitles='{ass_str}'"
    configured = str(pipeline_cfg.get("encoder") or "auto").lower()
    encoder = configured if configured in ENCODER_CODECS and configured != "auto" else os.environ.get("HIGHLIGHT_ENCODER", "cpu").lower()
    if encoder not in ENCODER_CODECS:
        encoder = "cpu"
    codec = ENCODER_CODECS[encoder]
    crf = str(pipeline_cfg.get("crf") or 21)

    def build_command(selected_encoder):
        selected_codec = ENCODER_CODECS[selected_encoder]
        command = [
            "ffmpeg", "-y", "-ss", str(start_time), "-t", str(duration),
            "-i", str(source_video), "-vf", vf, "-c:v", selected_codec,
        ]
        if selected_encoder == "cpu":
            command.extend(["-preset", "veryfast", "-crf", crf])
        elif selected_encoder == "nvenc":
            command.extend(["-preset", str(pipeline_cfg.get("nvenc_preset") or "p2"), "-cq", crf])
        elif selected_encoder == "qsv":
            command.extend(["-preset", "veryfast", "-global_quality", crf])
        else:
            command.extend(["-quality", "speed", "-qp_i", crf, "-qp_p", crf])
        command.extend(["-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output_path)])
        return command

    if update_status:
        update_status(f"Đang render bằng {codec} (tối đa {RENDER_CONCURRENCY} render đồng thời)...")
    with render_slot():
        cmd = build_command(encoder)
        rendered = subprocess.run(cmd, capture_output=True, text=True, creationflags=NO_WINDOW)
        if rendered.returncode != 0 and encoder != "cpu":
            print(f"[FFmpeg Warning] {codec} failed; fallback to libx264: {rendered.stderr[:300]}")
            rendered = subprocess.run(build_command("cpu"), capture_output=True, text=True, creationflags=NO_WINDOW)
        if rendered.returncode != 0:
            raise RuntimeError(f"FFmpeg render thất bại: {rendered.stderr}")

    return Path(output_path)




