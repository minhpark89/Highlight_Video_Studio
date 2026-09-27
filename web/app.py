import sys
from pathlib import Path
try:
    from core.website_article_service import WebsiteArticleService, WebsiteServiceError
    HAS_WEBSITE_SVC = True
except Exception as _e:
    WebsiteArticleService = None
    WebsiteServiceError = RuntimeError
    HAS_WEBSITE_SVC = False

import subprocess
import shutil
import sqlite3
import os
import sys
import json
import html
import requests
import uuid
import threading
from queue import Queue
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.chdir(str(ROOT_DIR))

from flask import Flask, request, jsonify, render_template, send_from_directory
# Lazy / safe imports for heavy processing modules
def get_pipeline_tools():
    from src.pipeline import (
        download_video_and_audio,
        get_youtube_transcript,
        transcribe_local_whisper,
        ask_llm_for_highlights,
        render_highlight_clip,
        extract_video_id
    )
    return download_video_and_audio, get_youtube_transcript, transcribe_local_whisper, ask_llm_for_highlights, render_highlight_clip, extract_video_id

def search_videos(*args, **kwargs):
    from src.research import search_videos as _sv
    return _sv(*args, **kwargs)

def generate_viral_content(*args, **kwargs):
    from src.content_builder import generate_viral_content as _gvc
    return _gvc(*args, **kwargs)

def render_stylish_thumbnail(*args, **kwargs):
    from src.content_builder import render_stylish_thumbnail as _rst
    return _rst(*args, **kwargs)

def test_and_pick_active_llm(*args, **kwargs):
    from src.content_builder import test_and_pick_active_llm as _tpl
    return _tpl(*args, **kwargs)

from src.publisher.token_vault import TokenVault
from src.publisher.page_manager import PageManager
from src.publisher.website_publisher import (
    publish_clip_to_website_cms,
    generate_curiosity_comment_with_llm,
    generate_llm_hook_image,
    get_clip_metadata,
)
from src.publisher.meta_reel_poster import MetaReelPoster


app = Flask(__name__, template_folder="templates", static_folder="static")

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


BASE_DIR = Path(str(Path(__file__).resolve().parent.parent))
DOWNLOADS_DIR = BASE_DIR / "downloads"
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"
JOBS_FILE = BASE_DIR / "jobs.json"
POSTS_FILE = BASE_DIR / "posts.json"
CRAWLED_VIDEOS_FILE = BASE_DIR / "crawled_videos.json"

def load_crawled_videos():
    if not CRAWLED_VIDEOS_FILE.exists():
        return []
    try:
        with open(CRAWLED_VIDEOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_crawled_videos(videos):
    try:
        with open(CRAWLED_VIDEOS_FILE, "w", encoding="utf-8") as f:
            json.dump(videos, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving crawled videos: {e}")

def load_posts():
    if not POSTS_FILE.exists():
        return []
    try:
        with open(POSTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_posts(posts):
    try:
        with open(POSTS_FILE, "w", encoding="utf-8") as f:
            json.dump(posts, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving posts: {e}")


for d in [DOWNLOADS_DIR, OUTPUT_DIR, TEMP_DIR]:
    d.mkdir(parents=True, exist_ok=True)

token_vault = TokenVault(BASE_DIR)
page_manager = PageManager(BASE_DIR)
reel_poster = MetaReelPoster(token_vault=token_vault)


JOBS_LOCK = threading.RLock()

def load_jobs():
    if not JOBS_FILE.exists():
        return []
    for _ in range(5):
        try:
            with open(JOBS_FILE, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().strip()
                if not content:
                    time.sleep(0.05)
                    continue
                # Try standard json parse first
                try:
                    return json.loads(content)
                except Exception:
                    # Fallback to strict=False or raw_decode to prevent empty queue bug
                    try:
                        return json.loads(content, strict=False)
                    except Exception:
                        decoder = json.JSONDecoder()
                        obj, _ = decoder.raw_decode(content)
                        return obj
        except Exception:
            time.sleep(0.05)
    return []

def save_jobs(jobs):
    """Atomically save jobs without sharing one temp filename between workers."""
    with JOBS_LOCK:
        if not jobs and JOBS_FILE.exists() and JOBS_FILE.stat().st_size > 100:
            return False
        tmp_file = JOBS_FILE.with_name(
            f"{JOBS_FILE.name}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp"
        )
        try:
            with open(tmp_file, "w", encoding="utf-8") as handle:
                json.dump(jobs, handle, indent=2, ensure_ascii=False)
                handle.flush()
                os.fsync(handle.fileno())
            for attempt in range(12):
                try:
                    os.replace(str(tmp_file), str(JOBS_FILE))
                    return True
                except PermissionError:
                    if attempt == 11:
                        raise
                    time.sleep(0.04 * (attempt + 1))
        finally:
            try:
                tmp_file.unlink(missing_ok=True)
            except Exception:
                pass
    return False

def update_job_status(job_id, updates):
    # Read-modify-write is one critical section so simultaneous worker updates
    # cannot overwrite each other with an older snapshot.
    with JOBS_LOCK:
        jobs = load_jobs()
        for job in jobs:
            if job.get("id") == job_id:
                job.update(updates)
                break
        return save_jobs(jobs)

def run_job_pipeline(job):
    job_id = job["id"]
    url = job["youtube_url"]
    num_clips = job.get("num_clips", 3)
    aspect_ratio = job.get("aspect_ratio", "9:16")
    reframe_mode = job.get("reframe_mode", "face_center")
    subtitle_style = job.get("subtitle_style", "hormozi_yellow")

    def update_msg(msg, step=1, status="running"):
        update_job_status(job_id, {
            "status": status,
            "step": step,
            "progress_msg": msg
        })

    try:
        (
            download_video_and_audio,
            get_youtube_transcript,
            transcribe_local_whisper,
            ask_llm_for_highlights,
            render_highlight_clip,
            extract_video_id,
        ) = get_pipeline_tools()
        # Bước 1: Tải video và audio
        update_msg("Đang tải video và bóc tách âm thanh siêu tốc (-N 8)...", step=1)
        dl_res = download_video_and_audio(url, job_id, update_status=lambda m: update_msg(m, step=1))
        video_path = dl_res['video_path']
        audio_path = dl_res['audio_path']
        title = dl_res['title']
        duration = dl_res['duration']
        
        update_job_status(job_id, {
            "video_title": title,
            "duration": duration,
            "video_path": str(video_path),
            "audio_path": str(audio_path)
        })

        # Bước 2: Bóc tách phụ đề / transcript
        update_msg("Đang trích xuất transcript (YouTube Subtitles / Local Whisper)...", step=2)
        v_id = extract_video_id(url)
        segments = []
        if v_id:
            segments = get_youtube_transcript(v_id)
        
        if not segments:
            update_msg("Không tìm thấy subtitle YouTube, kích hoạt Whisper CUDA float16...", step=2)
            segments = transcribe_local_whisper(audio_path)

        if not segments:
            raise RuntimeError("Không thể lấy phụ đề hoặc nhận diện giọng nói của video này.")

        # Bước 3: AI LLM phân tích Hook & Highlight
        update_msg("AI Gemini đang phân tích nội dung, chấm điểm Viral & cắt Hook...", step=3)
        highlights = ask_llm_for_highlights(segments, num_clips=num_clips, target_length=job.get("clip_length", "auto"), criteria=job.get("highlight_criteria", "hook_viral"), hook_duration=job.get("hook_duration", 6), update_status=lambda m: update_msg(m, step=3))
        if not highlights:
            raise RuntimeError("AI không thể tìm thấy đoạn highlight phù hợp.")

        # Bước 4 & 5: Smart Reframe & Render từng clip (kèm Dynamic Subtitle)
        update_msg(f"Bắt đầu render {len(highlights)} clips highlight 9:16 (NVENC Hardware GPU)...", step=4)
        rendered_clips = []
        for idx, h in enumerate(highlights, 1):
            update_msg(f"Đang render clip {idx}/{len(highlights)}: {h.get('title', 'Clip')}...", step=4)
            clip_file = render_highlight_clip(
                video_path=video_path,
                audio_path=audio_path,
                start_sec=h["start"],
                end_sec=h["end"],
                job_id=job_id,
                clip_idx=idx,
                output_dir=OUTPUT_DIR,
                aspect_ratio=aspect_ratio,
                reframe_mode=reframe_mode,
                subtitle_style=subtitle_style,
                all_segments=segments
            )
            if clip_file and clip_file.exists():
                rendered_clips.append({
                    "clip_index": idx,
                    "filename": clip_file.name,
                    "url": f"/api/clips/play/{clip_file.name}",
                    "title": h.get("title", f"Clip #{idx}"),
                    "reason": h.get("reason", ""),
                    "viral_score": h.get("viral_score", 85),
                    "start": h["start"],
                    "end": h["end"],
                    "duration": round(h["end"] - h["start"], 1)
                })

        update_job_status(job_id, {
            "status": "completed",
            "step": 5,
            "progress_msg": f"Hoàn tất! Đã xuất {len(rendered_clips)} clips highlight chất lượng cao.",
            "clips": rendered_clips
        })

    except Exception as e:
        update_job_status(job_id, {
            "status": "error",
            "progress_msg": f"Lỗi xử lý: {str(e)}"
        })


# ==========================================
# BACKGROUND QUEUE MANAGER FOR BATCH RENDERING
# ==========================================
MAX_CONCURRENT_JOBS = 2
JOB_QUEUE = Queue()
ACTIVE_JOB_IDS = set()
CANCELLED_JOB_IDS = set()
IS_QUEUE_PAUSED = False
QUEUE_LOCK = threading.Lock()

def queue_worker_loop():
    global IS_QUEUE_PAUSED
    while True:
        try:
            if IS_QUEUE_PAUSED:
                time.sleep(2)
                continue
                
            with QUEUE_LOCK:
                if len(ACTIVE_JOB_IDS) >= MAX_CONCURRENT_JOBS:
                    time.sleep(1)
                    continue

            # Check jobs.json for any pending queued jobs
            all_jobs = load_jobs()
            next_job = None
            for j in all_jobs:
                if j.get("status") == "queued" and j.get("id") not in ACTIVE_JOB_IDS and j.get("id") not in CANCELLED_JOB_IDS:
                    next_job = j
                    break

            if next_job:
                with QUEUE_LOCK:
                    ACTIVE_JOB_IDS.add(next_job["id"])
                
                # Start job thread
                def _run(job_data):
                    try:
                        run_job_pipeline(job_data)
                    finally:
                        with QUEUE_LOCK:
                            ACTIVE_JOB_IDS.discard(job_data["id"])
                            
                t = threading.Thread(target=_run, args=(next_job,), daemon=True)
                t.start()
            else:
                time.sleep(2)
        except Exception as e:
            print(f"[QueueWorker] Error: {e}")
            time.sleep(2)

# Start queue background thread
_queue_thread = threading.Thread(target=queue_worker_loop, daemon=True)
_queue_thread.start()

# Start scheduled posts publisher background thread (LoHa Page standard)
try:
    from web.scheduled_publisher import scheduled_publisher_worker_loop
except ImportError:
    from scheduled_publisher import scheduled_publisher_worker_loop
_publisher_thread = threading.Thread(target=scheduled_publisher_worker_loop, daemon=True)
_publisher_thread.start()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    return jsonify(load_jobs())

@app.route("/api/jobs/<job_id>", methods=["GET"])
def get_job(job_id):
    jobs = load_jobs()
    for j in jobs:
        if j["id"] == job_id:
            return jsonify(j)
    return jsonify({"error": "Job not found"}), 404

@app.route("/api/jobs", methods=["POST"])
def create_job():
    data = request.json or {}
    raw_url = data.get("youtube_url", "")
    urls_input = data.get("youtube_urls", [])
    
    urls = []
    if isinstance(raw_url, str) and raw_url.strip():
        # Split by newline or comma or whitespace if multiple
        for line in raw_url.replace(',', '\n').splitlines():
            line = line.strip()
            if line and ('youtube.com' in line or 'youtu.be' in line or 'http' in line):
                urls.append(line)
            elif line and len(line) == 11 and not ' ' in line: # raw ID
                urls.append(f"https://www.youtube.com/watch?v={line}")
    if isinstance(urls_input, list):
        for u in urls_input:
            if isinstance(u, str) and u.strip():
                urls.append(u.strip())
                
    # Deduplicate while preserving order
    unique_urls = []
    for u in urls:
        if u not in unique_urls:
            unique_urls.append(u)
            
    if not unique_urls:
        return jsonify({"error": "Vui lòng nhập ít nhất 1 đường link YouTube hợp lệ."}), 400

    created_jobs = []
    jobs = load_jobs()
    
    for url in unique_urls:
        job_id = f"job_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        job = {
            "id": job_id,
            "youtube_url": url,
            "clip_length": data.get("clip_length", "auto"),
            "hook_duration": int(data.get("hook_duration", 6)),
            "num_clips": int(data.get("num_clips", 3)),
            "aspect_ratio": data.get("aspect_ratio", "9:16"),
            "reframe_mode": data.get("reframe_mode", "face_center"),
            "subtitle_style": data.get("subtitle_style", "hormozi_yellow"),
            "highlight_criteria": data.get("highlight_criteria", "hook_viral"),
            "status": "queued",
            "step": 0,
            "progress_msg": "Đang chờ trong hàng đợi...",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "clips": []
        }
        jobs.insert(0, job)
        created_jobs.append(job)
        time.sleep(0.005)

    save_jobs(jobs)

    return jsonify({
        "success": True, 
        "job_id": created_jobs[0]["id"], 
        "job_ids": [j["id"] for j in created_jobs],
        "count": len(created_jobs)
    })


@app.route("/api/jobs/<job_id>/retry", methods=["POST"])
def retry_job(job_id):
    jobs = load_jobs()
    found = False
    for j in jobs:
        if j.get("id") == job_id:
            j["status"] = "queued"
            j.pop("error", None)
            j["progress"] = 0
            j["step"] = "Queued for retry"
            found = True
            break
    if found:
        save_jobs(jobs)
        return jsonify({"success": True, "message": f"Job {job_id} requeued"})
    return jsonify({"error": "Job not found"}), 404

@app.route("/api/jobs/retry_failed", methods=["POST"])
def retry_all_failed_jobs():
    jobs = load_jobs()
    count = 0
    for j in jobs:
        if j.get("status") == "error":
            j["status"] = "queued"
            j.pop("error", None)
            j["progress"] = 0
            j["step"] = "Queued for retry"
            count += 1
    if count > 0:
        save_jobs(jobs)
    return jsonify({"success": True, "count": count, "message": f"Requeued {count} failed jobs"})

@app.route("/api/jobs/<job_id>", methods=["DELETE"])
def delete_job(job_id):
    jobs = load_jobs()
    jobs = [j for j in jobs if j["id"] != job_id]
    save_jobs(jobs)
    return jsonify({"success": True})

@app.route("/api/clips", methods=["GET"])
def get_all_clips():
    jobs = load_jobs()
    all_clips = []
    posted_file = BASE_DIR / "posted_clips.json"
    posted_set = set()
    if posted_file.exists():
        try:
            import json
            posted_set = set(json.loads(posted_file.read_text(encoding="utf-8")))
        except:
            pass

    seen_files = set()
    # Chỉ lấy các clip có file video THỰC TẾ đang tồn tại trên ổ đĩa máy này
    for j in jobs:
        for c in j.get("clips", []):
            fn = c.get("filename")
            if fn:
                clip_path = OUTPUT_DIR / fn
                if not clip_path.exists():
                    continue # Bỏ qua nếu file video không có trên máy tính này
                seen_files.add(fn)
                clip_copy = dict(c)
                clip_copy["job_id"] = j["id"]
                clip_copy["video_source"] = j.get("video_title", j.get("youtube_url"))
                clip_copy["is_posted"] = (fn in posted_set)
                all_clips.append(clip_copy)
            
    # Quét trực tiếp các video .mp4 thực tế trong thư mục output/
    if OUTPUT_DIR.exists():
        for f in sorted(OUTPUT_DIR.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.name not in seen_files:
                seen_files.add(f.name)
                all_clips.append({
                    "filename": f.name,
                    "title": f.stem,
                    "duration": 0,
                    "file_size": f.stat().st_size,
                    "is_posted": (f.name in posted_set),
                    "job_id": "direct_scan",
                    "video_source": "Kho video thực tế"
                })
                
    return jsonify(all_clips)

@app.route("/api/clips/play/<path:filename>")
def play_clip(filename):
    return send_from_directory(str(OUTPUT_DIR), filename)


@app.route("/api/clips/<path:filename>", methods=["DELETE"])
def api_delete_clip(filename):
    try:
        file_path = OUTPUT_DIR / filename
        if file_path.exists():
            file_path.unlink()
        
        # Also clean up from jobs
        jobs = load_jobs()
        updated = False
        for j in jobs:
            clips = j.get("clips", [])
            new_clips = [c for c in clips if c.get("filename") != filename]
            if len(new_clips) != len(clips):
                j["clips"] = new_clips
                updated = True
        if updated:
            save_jobs(jobs)

        # Clean from posts/markings if any
        return jsonify({"success": True, "message": f"Đã xóa clip {filename}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/clips/mark_posted", methods=["POST"])
def api_mark_clip_posted():
    try:
        data = request.json or {}
        filename = data.get("filename")
        if not filename:
            return jsonify({"success": False, "error": "Thiếu filename"}), 400

        posted_file = BASE_DIR / "posted_clips.json"
        posted_data = []
        if posted_file.exists():
            try:
                import json
                posted_data = json.loads(posted_file.read_text(encoding="utf-8"))
            except:
                posted_data = []

        if filename not in posted_data:
            posted_data.append(filename)
            import json
            posted_file.write_text(json.dumps(posted_data, indent=2, ensure_ascii=False), encoding="utf-8")

        return jsonify({"success": True, "posted_clips": posted_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/research", methods=["POST"])
def api_research():
    data = request.json or {}
    query = data.get("query", "").strip()
    platform = data.get("platform", "youtube")
    filter_type = data.get("filter_type", "all")
    max_results = int(data.get("max_results", 12))

    if not query:
        return jsonify({"error": "Query or URL is required", "results": []}), 400

    try:
        results = search_videos(query=query, platform=platform, max_results=max_results, filter_type=filter_type)
        if results:
            saved = load_crawled_videos()
            existing_urls = {v.get("url") for v in saved if v.get("url")}
            new_added = 0
            for r in results:
                u = r.get("url")
                if u and u not in existing_urls:
                    r_copy = dict(r)
                    r_copy["status"] = "new"
                    r_copy["crawled_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    saved.insert(0, r_copy)
                    existing_urls.add(u)
                    new_added += 1
            if new_added > 0:
                save_crawled_videos(saved)
        return jsonify({"success": True, "results": results, "count": len(results)})
    except Exception as e:
        return jsonify({"error": str(e), "results": []}), 500

@app.route("/api/research/saved", methods=["GET"])
def api_research_saved():
    saved = load_crawled_videos()
    return jsonify({"success": True, "results": saved, "count": len(saved)})

@app.route("/api/research/mark_used", methods=["POST"])
def api_research_mark_used():
    data = request.json or {}
    target_urls = set(data.get("urls", []))
    if not target_urls:
        return jsonify({"success": True, "updated": 0})
    saved = load_crawled_videos()
    updated = 0
    for v in saved:
        if v.get("url") in target_urls:
            v["status"] = "used"
            updated += 1
    if updated > 0:
        save_crawled_videos(saved)
    return jsonify({"success": True, "updated": updated})

@app.route("/api/research/clear", methods=["POST"])
def api_research_clear():
    data = request.json or {}
    mode = data.get("mode", "clear_used")
    saved = load_crawled_videos()
    if mode == "clear_all":
        saved = []
    elif mode == "clear_used":
        saved = [v for v in saved if v.get("status") != "used"]
    save_crawled_videos(saved)
    return jsonify({"success": True, "count": len(saved)})



CONFIG_FILE = BASE_DIR / "config.json"

def load_config():
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False

def public_config(cfg):
    """Return UI-safe settings without exposing saved credentials to browsers."""
    safe = json.loads(json.dumps(cfg or {}))
    llm = safe.get("llm")
    if isinstance(llm, dict):
        llm["has_api_key"] = bool(llm.get("api_key"))
        llm.pop("api_key", None)
    image_provider = safe.get("image_provider")
    if isinstance(image_provider, dict):
        image_provider["has_api_key"] = bool(image_provider.get("api_key"))
        image_provider.pop("api_key", None)
    return safe


def _normalise_llm_base(raw_base):
    from urllib.parse import urlsplit, urlunsplit

    value = str(raw_base or "").strip().rstrip("/")
    if not value:
        raise ValueError("Vui lòng nhập LLM Provider Endpoint")
    parsed = urlsplit(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Endpoint phải là URL http:// hoặc https:// hợp lệ")
    path = parsed.path.rstrip("/")
    lower_path = path.lower()
    for suffix in ("/chat/completions", "/completions", "/models"):
        if lower_path.endswith(suffix):
            path = path[:-len(suffix)].rstrip("/")
            break
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", "")).rstrip("/")


def _llm_model_urls(raw_base):
    base = _normalise_llm_base(raw_base)
    urls = [f"{base}/models"]
    if not base.lower().endswith("/v1"):
        urls.append(f"{base}/v1/models")
    return list(dict.fromkeys(urls))


def _normalise_http_url(raw_url, field_name="Endpoint"):
    from urllib.parse import urlsplit, urlunsplit

    value = str(raw_url or "").strip()
    if not value:
        raise ValueError(f"Vui lòng nhập {field_name}")
    parsed = urlsplit(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"{field_name} phải là URL http:// hoặc https:// hợp lệ")
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), parsed.query, ""))


def _image_model_urls(models_url="", api_base=""):
    if str(models_url or "").strip():
        return [_normalise_http_url(models_url, "Endpoint lấy model ảnh")]
    return _llm_model_urls(api_base)


def _image_generation_candidates(generation_url="", api_base=""):
    exact = str(generation_url or "").strip()
    if exact:
        url = _normalise_http_url(exact, "Endpoint tạo ảnh")
        lower = url.lower().split("?", 1)[0]
        if lower.endswith("/images/generations"):
            return [(url, "images")]
        if lower.endswith("/chat/completions"):
            return [(url, "chat")]
        return [(url, "auto")]
    base = _normalise_llm_base(api_base)
    return [
        (f"{base}/images/generations", "images"),
        (f"{base}/chat/completions", "chat"),
    ]


def _image_test_payload(model, endpoint_type):
    prompt = "A simple blue circle on white background"
    if endpoint_type == "chat":
        return {"model": model, "messages": [{"role": "user", "content": prompt}]}
    return {"model": model, "prompt": prompt, "n": 1, "size": "1024x1024"}


def _image_response_has_output(payload):
    if not isinstance(payload, dict):
        return False
    rows = payload.get("data") or []
    if rows and isinstance(rows[0], dict) and (rows[0].get("b64_json") or rows[0].get("url")):
        return True
    choices = payload.get("choices") or []
    message = choices[0].get("message", {}) if choices and isinstance(choices[0], dict) else {}
    images = message.get("images") or []
    if images:
        return True
    content = message.get("content")
    return isinstance(content, str) and ("data:image/" in content or "http://" in content or "https://" in content)


def _extract_llm_models(payload):
    if isinstance(payload, dict):
        rows = payload.get("data")
        if not isinstance(rows, list):
            rows = payload.get("models")
    elif isinstance(payload, list):
        rows = payload
    else:
        rows = None
    models = []
    for row in rows or []:
        if isinstance(row, str):
            model_id = row
        elif isinstance(row, dict):
            model_id = row.get("id") or row.get("name") or row.get("model")
            if isinstance(model_id, str) and model_id.startswith("models/"):
                model_id = model_id.split("/", 1)[1]
        else:
            model_id = None
        if model_id and model_id not in models:
            models.append(model_id)
    return sorted(models, key=str.lower)


def _llm_headers(api_key):
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if api_key:
        headers.update({
            "Authorization": f"Bearer {api_key}",
            "x-api-key": api_key,
            "api-key": api_key,
        })
    return headers

def detect_hardware():
    import platform
    import subprocess
    node_name = platform.node()
    cpu_name = platform.processor() or "x86_64 Processor"
    gpu_name = "CPU Only (Không phát hiện GPU rời)"
    has_nvidia = False

    try:
        out = subprocess.check_output("wmic path win32_VideoController get name", shell=True, text=True, stderr=subprocess.DEVNULL)
        lines = [l.strip() for l in out.splitlines() if l.strip() and l.strip().lower() != 'name']
        if lines:
            gpu_name = " / ".join(lines)
            if any(k in gpu_name.lower() for k in ["nvidia", "geforce", "rtx", "gtx", "quadro", "tesla"]):
                has_nvidia = True
    except Exception:
        pass

    return {
        "hostname": node_name,
        "cpu": cpu_name,
        "gpu": gpu_name,
        "has_nvidia": has_nvidia,
        "recommended_encoder": "h264_nvenc" if has_nvidia else "libx264"
    }


@app.route("/api/system/youtube_status", methods=["GET"])
def api_youtube_status():
    """Kiểm tra xem Chrome profile đã đăng nhập YouTube hay chưa dựa trên cookies xác thực Google/YouTube."""
    candidate_dirs = [
        ROOT_DIR / "chrome_profile",
        Path(r"F:\openclaw\.openclaw\workspace\chrome_profile")
    ]
    profiles = ["Default", "Profile 1", "Profile 2", "Profile 3"]
    total_cnt = 0

    for base_dir in candidate_dirs:
        if not base_dir.exists():
            continue
        for prof in profiles:
            cookie_path = base_dir / prof / "Network" / "Cookies"
            if not cookie_path.exists():
                continue

            temp_db = base_dir / f"temp_yt_{prof}_{int(time.time()*1000)}.db"
            try:
                shutil.copyfile(str(cookie_path), str(temp_db))
                conn = sqlite3.connect(str(temp_db))
                cur = conn.cursor()
                # Kiểm tra cả domain google.com và youtube.com vì đăng nhập tài khoản Google cấp cookie SID/SSID/SAPISID
                cur.execute("""
                    SELECT COUNT(*) FROM cookies 
                    WHERE (host_key LIKE '%youtube.com%' OR host_key LIKE '%google.com%') 
                      AND name IN ('LOGIN_INFO', 'SID', 'SSID', 'SAPISID', 'HSID', '__Secure-1PSID', '__Secure-3PSID', 'APISID')
                """)
                row = cur.fetchone()
                cnt = row[0] if row else 0
                conn.close()
                total_cnt += cnt
                if cnt > 0:
                    return jsonify({"logged_in": True, "count": cnt, "profile": prof})
            except Exception:
                pass
            finally:
                if temp_db.exists():
                    try:
                        temp_db.unlink()
                    except Exception:
                        pass

    return jsonify({"logged_in": total_cnt > 0, "count": total_cnt})

@app.route("/api/system/open_chrome", methods=["POST"])
def api_open_chrome():
    try:
        data = request.json or {}
        platform = data.get("platform", "youtube").lower()
        target_urls = {
            "youtube": "https://www.youtube.com",
            "facebook": "https://www.facebook.com",
            "tiktok": "https://www.tiktok.com",
            "blank": "about:blank"
        }
        target_url = target_urls.get(platform, "https://www.youtube.com")
        
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe")
        ]
        
        chrome_exe = None
        for p in chrome_paths:
            if os.path.exists(p):
                chrome_exe = p
                break
                
        if not chrome_exe:
            return jsonify({"success": False, "error": "Không tìm thấy Google Chrome tại C:\Program Files\Google\Chrome\Application\chrome.exe"}), 404
            
        profile_dir = ROOT_DIR / "chrome_profile"
        profile_dir.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            chrome_exe,
            f"--user-data-dir={str(profile_dir)}",
            "--no-first-run",
            "--no-default-browser-check",
            target_url
        ]
        
        subprocess.Popen(cmd, creationflags=getattr(subprocess, 'DETACHED_PROCESS', 0) | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0))
        return jsonify({
            "success": True,
            "platform": platform,
            "target_url": target_url,
            "profile_dir": str(profile_dir),
            "message": f"Đã mở Chrome ({platform.upper()}) với profile độc lập của App!"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/system/info", methods=["GET"])
def api_system_info():
    hw = detect_hardware()
    cfg = load_config()
    return jsonify({
        "success": True,
        "hardware": hw,
        "config": public_config(cfg)
    })

@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    if request.method == "POST":
        data = request.json or {}
        cfg = load_config()
        if "llm" in data:
            llm_update = dict(data["llm"] or {})
            if "api_base" in llm_update:
                try:
                    llm_update["api_base"] = _normalise_llm_base(llm_update["api_base"])
                except ValueError as exc:
                    return jsonify({"success": False, "error": str(exc)}), 400
            cfg.setdefault("llm", {}).update(llm_update)
        if "image_provider" in data:
            image_update = dict(data["image_provider"] or {})
            frame_mode = str(image_update.get("model") or "") == "__video_frame__"
            try:
                if str(image_update.get("models_url") or "").strip():
                    image_update["models_url"] = _normalise_http_url(image_update["models_url"], "Endpoint lấy model ảnh")
                if str(image_update.get("generation_url") or "").strip():
                    image_update["generation_url"] = _normalise_http_url(image_update["generation_url"], "Endpoint tạo ảnh")
                if str(image_update.get("api_base") or "").strip():
                    image_update["api_base"] = _normalise_llm_base(image_update["api_base"])
            except ValueError as exc:
                return jsonify({"success": False, "error": f"Image Provider: {exc}"}), 400
            if not frame_mode and not str(image_update.get("generation_url") or image_update.get("api_base") or "").strip():
                return jsonify({"success": False, "error": "Image Provider: vui lòng nhập endpoint tạo ảnh khi dùng AI ảnh"}), 400
            cfg.setdefault("image_provider", {}).update(image_update)
        if "video_pipeline" in data:
            cfg.setdefault("video_pipeline", {}).update(data["video_pipeline"])
        if "whisper" in data:
            cfg.setdefault("whisper", {}).update(data["whisper"])
        
        saved = save_config(cfg)
        return jsonify({"success": saved, "config": cfg})
    else:
        return jsonify({"success": True, "config": public_config(load_config())})


@app.route("/api/llm/models", methods=["POST"])
def api_llm_models():
    data = request.json or {}
    cfg_llm = load_config().get("llm", {})
    raw_base = data.get("api_base") or cfg_llm.get("api_base")
    api_key = data.get("api_key") or cfg_llm.get("api_key", "")
    try:
        model_urls = _llm_model_urls(raw_base)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    failures = []
    for models_url in model_urls:
        try:
            response = requests.get(models_url, headers=_llm_headers(api_key), timeout=15)
            if response.status_code != 200:
                try:
                    detail = response.json().get("error") or response.json().get("message") or ""
                    if isinstance(detail, dict):
                        detail = detail.get("message") or str(detail)
                except Exception:
                    detail = response.text[:180].strip()
                failures.append(f"{models_url}: HTTP {response.status_code}" + (f" - {detail}" if detail else ""))
                continue
            models = _extract_llm_models(response.json())
            if not models:
                failures.append(f"{models_url}: response không có danh sách model")
                continue
            return jsonify({
                "success": True,
                "api_base": models_url[:-len("/models")].rstrip("/"),
                "models": models,
                "count": len(models),
            })
        except requests.RequestException as exc:
            failures.append(f"{models_url}: {exc}")
        except ValueError:
            failures.append(f"{models_url}: server không trả JSON hợp lệ")
    return jsonify({"success": False, "error": "Không thể lấy danh sách model. " + " | ".join(failures)}), 502


@app.route("/api/image-provider/models", methods=["POST"])
def api_image_provider_models():
    data = request.json or {}
    image_cfg = load_config().get("image_provider", {})
    raw_base = data.get("api_base") or image_cfg.get("api_base")
    models_url = data.get("models_url") or image_cfg.get("models_url")
    api_key = data.get("api_key") or image_cfg.get("api_key", "")
    try:
        model_urls = _image_model_urls(models_url, raw_base)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    failures = []
    for candidate_url in model_urls:
        try:
            response = requests.get(candidate_url, headers=_llm_headers(api_key), timeout=15)
            if response.status_code != 200:
                failures.append(f"{candidate_url}: HTTP {response.status_code}")
                continue
            models = _extract_llm_models(response.json())
            if models:
                return jsonify({"success": True, "models_url": candidate_url, "models": models, "count": len(models)})
            failures.append(f"{candidate_url}: response không có danh sách model")
        except Exception as exc:
            failures.append(f"{candidate_url}: {exc}")
    return jsonify({"success": False, "error": "Endpoint lấy model không hoạt động; vẫn có thể nhập model thủ công và Test tạo ảnh. " + " | ".join(failures)}), 502


@app.route("/api/image-provider/test", methods=["POST"])
def api_image_provider_test():
    data = request.json or {}
    image_cfg = load_config().get("image_provider", {})
    raw_base = data.get("api_base") or image_cfg.get("api_base")
    generation_url = data.get("generation_url") or image_cfg.get("generation_url")
    api_key = data.get("api_key") or image_cfg.get("api_key", "")
    model = str(data.get("model") or image_cfg.get("model") or "").strip()
    if not model or model == "__video_frame__":
        return jsonify({"success": False, "error": "Vui lòng nhập model tạo ảnh"}), 400
    try:
        candidates = _image_generation_candidates(generation_url, raw_base)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    failures = []
    started = time.perf_counter()
    for url, endpoint_type in candidates:
        request_type = endpoint_type if endpoint_type != "auto" else ("chat" if url.lower().split("?", 1)[0].endswith("/chat/completions") else "images")
        try:
            response = requests.post(url, headers=_llm_headers(api_key), json=_image_test_payload(model, request_type), timeout=120)
            latency_ms = int((time.perf_counter() - started) * 1000)
            try:
                payload = response.json()
            except Exception:
                payload = {}
            if response.status_code == 200 and _image_response_has_output(payload):
                return jsonify({"success": True, "generation_url": url, "endpoint_type": request_type, "model": model, "latency_ms": latency_ms})
            detail = payload.get("error") or payload.get("message") or response.text[:240]
            if isinstance(detail, dict):
                detail = detail.get("message") or str(detail)
            if response.status_code == 200:
                detail = "HTTP 200 nhưng response không có dữ liệu ảnh"
            failures.append(f"{url}: HTTP {response.status_code} - {detail}")
        except requests.RequestException as exc:
            failures.append(f"{url}: {exc}")
    return jsonify({"success": False, "error": "Test tạo ảnh thất bại. " + " | ".join(failures)}), 502


@app.route("/api/llm/test", methods=["POST"])
def api_llm_test():
    data = request.json or {}
    cfg_llm = load_config().get("llm", {})
    raw_base = data.get("api_base") or cfg_llm.get("api_base")
    api_key = data.get("api_key") or cfg_llm.get("api_key", "")
    model = str(data.get("model") or cfg_llm.get("model") or "").strip()
    if not model:
        return jsonify({"success": False, "error": "Vui lòng chọn model cần kiểm tra"}), 400
    try:
        api_base = _normalise_llm_base(raw_base)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    started = time.perf_counter()
    try:
        response = requests.post(
            f"{api_base}/chat/completions",
            headers=_llm_headers(api_key),
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
                "max_tokens": 8,
                "temperature": 0,
            },
            timeout=30,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        try:
            payload = response.json()
        except Exception:
            payload = {}
        if response.status_code != 200:
            detail = payload.get("error") or payload.get("message") or response.text[:240]
            if isinstance(detail, dict):
                detail = detail.get("message") or str(detail)
            return jsonify({
                "success": False,
                "error": f"Model có trong danh sách nhưng gọi chat thất bại (HTTP {response.status_code}): {detail}",
                "latency_ms": latency_ms,
            }), 502
        choices = payload.get("choices") or []
        content = ""
        if choices and isinstance(choices[0], dict):
            content = str((choices[0].get("message") or {}).get("content") or choices[0].get("text") or "").strip()
        if not content:
            return jsonify({"success": False, "error": "Provider trả HTTP 200 nhưng không có nội dung chat"}), 502
        return jsonify({
            "success": True,
            "api_base": api_base,
            "model": model,
            "latency_ms": latency_ms,
            "sample": content[:80],
        })
    except requests.RequestException as exc:
        return jsonify({"success": False, "error": f"Không kết nối được model: {exc}"}), 502


@app.route("/api/content/generate", methods=["POST"])
def api_generate_content():
    data = request.json or {}
    title = data.get("title", "").strip()
    summary = data.get("summary", "").strip()
    hook = data.get("hook", "").strip()
    video_url = data.get("video_url", "").strip()
    comment_model = data.get("comment_model", "").strip()
    
    if not title:
        return jsonify({"error": "Title is required"}), 400
        
    res = generate_viral_content(
        title=title,
        summary=summary,
        hook=hook,
        video_url=video_url,
        comment_model=comment_model,
    )
    return jsonify({"success": True, "data": res})

@app.route("/api/content/thumbnail", methods=["POST"])
def api_generate_thumbnail():
    data = request.json or {}
    job_id = data.get("job_id", "")
    clip_index = data.get("clip_index", 1)
    banner_text = data.get("banner_text", "")
    image_model = data.get("image_model", "").strip()

    # Dùng model ảnh theo tác vụ khi được chọn; nếu provider không trả ảnh,
    # tiếp tục fallback sang thumbnail trích từ video để luồng không bị chặn.
    if image_model != "__video_frame__":
        ai_thumb = generate_llm_hook_image(banner_text or "VIRAL MOMENT", model_override=image_model)
        if ai_thumb and os.path.exists(ai_thumb):
            ai_name = f"thumb_ai_{job_id or 'clip'}_{clip_index}_{int(time.time())}.jpg"
            ai_target = OUTPUT_DIR / ai_name
            shutil.copy2(ai_thumb, ai_target)
            return jsonify({
                "success": True,
                "thumbnail_url": f"/api/clips/play/{ai_name}",
                "filename": ai_name,
                "source": "llm_image",
            })
    
    # Tìm video file của clip hoặc source video
    target_video = None
    if job_id:
        # Kiểm tra file clip trước
        clip_file = OUTPUT_DIR / f"{job_id}_clip_{clip_index}.mp4"
        if clip_file.exists():
            target_video = clip_file
        else:
            source_file = DOWNLOADS_DIR / f"{job_id}.mp4"
            if source_file.exists():
                target_video = source_file
                
    if not target_video or not target_video.exists():
        # Lấy bất kỳ clip nào trong output để test nếu cần
        clips = list(OUTPUT_DIR.glob("*.mp4"))
        if clips:
            target_video = clips[0]
            
    if not target_video:
        return jsonify({"error": "Không tìm thấy file video để tạo thumbnail"}), 404
        
    out_thumb_name = f"thumb_{job_id or 'clip'}_{clip_index}_{int(time.time())}.jpg"
    out_thumb_path = OUTPUT_DIR / out_thumb_name
    
    res_path = render_stylish_thumbnail(
        video_path=str(target_video),
        output_path=str(out_thumb_path),
        banner_text=banner_text or "VIRAL MOMENT",
        timestamp_sec=2.5
    )
    
    if res_path and os.path.exists(res_path):
        return jsonify({
            "success": True,
            "thumbnail_url": f"/api/clips/play/{out_thumb_name}",
            "filename": out_thumb_name
        })
    else:
        return jsonify({"error": "Không thể render thumbnail"}), 500

@app.route("/api/llm/detect", methods=["GET"])
def api_llm_detect():
    info = test_and_pick_active_llm()
    return jsonify({"success": True, "active_llm": info})

# (main moved to end of file)




# ================= QUẢN LÝ NHÓM TOKEN (LOHA TOKEN GROUPS) =================
TOKEN_GROUPS_FILE = BASE_DIR / "token_groups.json"

def load_token_groups():
    if not TOKEN_GROUPS_FILE.exists():
        # Mặc định tạo Nhóm AutoPool 31 Token
        default_groups = [{
            "id": "tgrp_autopool",
            "name": "Nhóm AutoPool Chính (31 Token)",
            "strategy": "least_recently_used", # round_robin | least_recently_used | random
            "token_ids": [t.get("id") for t in token_vault.list_tokens(mask=False)],
            "note": "Xoay vòng 31 token chống quá tải Meta",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }]
        with open(TOKEN_GROUPS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_groups, f, indent=2, ensure_ascii=False)
        return default_groups
    try:
        with open(TOKEN_GROUPS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_token_groups(groups):
    with open(TOKEN_GROUPS_FILE, "w", encoding="utf-8") as f:
        json.dump(groups, f, indent=2, ensure_ascii=False)

@app.route("/api/token-groups", methods=["GET"])
def api_list_token_groups():
    return jsonify({"success": True, "groups": load_token_groups()})

@app.route("/api/token-groups", methods=["POST"])
def api_save_token_group():
    data = request.json or {}
    gid = data.get("id") or f"tgrp_{int(time.time())}"
    name = data.get("name", "").strip()
    token_ids = data.get("token_ids", [])
    strategy = data.get("strategy", "least_recently_used")
    note = data.get("note", "").strip()

    if not name:
        return jsonify({"error": "Tên nhóm token không được rỗng"}), 400

    groups = load_token_groups()
    existing = next((g for g in groups if g.get("id") == gid), None)
    if existing:
        existing["name"] = name
        existing["token_ids"] = token_ids
        existing["strategy"] = strategy
        existing["note"] = note
        existing["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        groups.append({
            "id": gid,
            "name": name,
            "strategy": strategy,
            "token_ids": token_ids,
            "note": note,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    save_token_groups(groups)
    return jsonify({"success": True, "message": f"Đã lưu Nhóm Token '{name}' thành công!"})

@app.route("/api/token-groups/<gid>", methods=["DELETE"])
def api_delete_token_group(gid):
    groups = load_token_groups()
    new_groups = [g for g in groups if g.get("id") != gid]
    save_token_groups(new_groups)
    return jsonify({"success": True, "message": "Đã xóa nhóm token!"})


@app.route("/api/tokens", methods=["GET"])
def api_list_tokens():
    tokens = token_vault.list_tokens(mask=True)
    return jsonify({"success": True, "tokens": tokens})

@app.route("/api/tokens", methods=["POST"])
def api_add_token():
    data = request.json or {}
    raw_tokens_input = data.get("tokens_input") or data.get("token") or ""
    raw_tokens_input = str(raw_tokens_input).strip()
    default_name = data.get("name", "").strip()
    kind = data.get("kind", "SYS")
    note = data.get("note", "").strip()
    
    if not raw_tokens_input:
        return jsonify({"error": "Thiếu mã token"}), 400
    
    # Check if multiple lines or single
    lines = [l.strip() for l in raw_tokens_input.splitlines() if l.strip()]
    if not lines:
        return jsonify({"error": "Nội dung token không hợp lệ"}), 400

    results = []
    synced_page_ids = set()
    
    for idx, line in enumerate(lines):
        # Format support: "Name|Token" or "Name,Token" or just "Token"
        item_name = default_name
        item_token = line
        if "|" in line:
            parts = line.split("|", 1)
            item_name = parts[0].strip() or default_name
            item_token = parts[1].strip()
        elif "," in line and not line.startswith("EAAB") and not line.startswith("EAA"):
            parts = line.split(",", 1)
            item_name = parts[0].strip() or default_name
            item_token = parts[1].strip()
            
        if not item_name:
            item_name = f"Token {idx + 1}" if len(lines) > 1 else "System Token"
            
        try:
            entry, pages = token_vault.add_token(item_name, item_token, kind, note)
            if pages:
                page_manager.sync_pages_from_token(entry, pages)
                for p in pages:
                    pid = p.get("id") or p.get("page_id")
                    if pid:
                        synced_page_ids.add(str(pid))
            results.append({
                "id": entry.get("id"),
                "name": entry.get("name"),
                "status": entry.get("status"),
                "error_msg": entry.get("error_msg", ""),
                "pages_count": len(pages)
            })
        except Exception as ex:
            results.append({
                "name": item_name,
                "status": "ERROR",
                "error_msg": str(ex),
                "pages_count": 0
            })
            
    return jsonify({
        "success": True,
        "count": len(results),
        "results": results,
        "synced_pages": len(synced_page_ids),
        "token": results[0] if results else None
    })

@app.route("/api/tokens/<token_id>", methods=["DELETE"])
def api_delete_token(token_id):
    ok = token_vault.delete_token(token_id)
    return jsonify({"success": ok})

@app.route("/api/pages", methods=["GET"])
def api_list_pages():
    pages = page_manager.list_pages()
    groups = page_manager.list_groups()
    return jsonify({"success": True, "pages": pages, "groups": groups})

@app.route("/api/groups", methods=["GET"])
def api_list_groups():
    groups = page_manager.list_groups()
    return jsonify({"success": True, "groups": groups})

@app.route("/api/groups", methods=["POST"])
def api_save_group():
    data = request.json or {}
    group_id = data.get("id") or data.get("group_id")
    name = data.get("name", "").strip()
    page_ids = data.get("page_ids", [])
    folder_binding = data.get("folder_binding") or data.get("folder_path") or str(OUTPUT_DIR)
    schedule_config = data.get("schedule_config")
    if not name:
        return jsonify({"error": "Tên nhóm không được để trống"}), 400
    
    group = page_manager.add_or_update_group(group_id, name, page_ids, folder_binding, schedule_config)
    gid = group.get("id")

    # Đồng bộ tên nhóm trực tiếp vào từng page trong pages.json để hiển thị tức thì
    try:
        pages = page_manager.list_pages()
        pages_updated = False
        pid_set = set(str(pid) for pid in page_ids)
        for p in pages:
            cur_pid = str(p.get("page_id") or p.get("id"))
            if cur_pid in pid_set:
                p["group_name"] = name
                g_ids = p.get("group_ids", [])
                if gid not in g_ids:
                    g_ids.append(gid)
                p["group_ids"] = g_ids
                pages_updated = True
        if pages_updated:
            page_manager.save_pages(pages)
    except Exception as ex:
        print("[Error syncing group to pages]", ex)

    return jsonify({"success": True, "group": group})

@app.route("/api/groups/<group_id>", methods=["DELETE"])
def api_delete_group(group_id):
    ok = page_manager.delete_group(group_id)
    if ok:
        # Gỡ nhóm khỏi các page đang mang nhóm này
        try:
            pages = page_manager.list_pages()
            pages_updated = False
            for p in pages:
                g_ids = p.get("group_ids", [])
                if group_id in g_ids or p.get("group_id") == group_id:
                    p["group_ids"] = [g for g in g_ids if g != group_id]
                    p["group_name"] = "Chưa nhóm"
                    pages_updated = True
            if pages_updated:
                page_manager.save_pages(pages)
        except Exception as ex:
            print("[Error cleaning group from pages]", ex)
    return jsonify({"success": ok})

@app.route("/api/publish/reel", methods=["POST"])
def api_publish_reel():
    data = request.json or {}
    page_id = data.get("page_id")
    page_ids = data.get("page_ids") or []
    group_id = data.get("group_id")
    clip_filename = data.get("filename")
    title = data.get("title", "")
    caption = data.get("caption", "")
    first_comment = data.get("first_comment", "")
    schedule_time = data.get("schedule_time") # ISO or "YYYY-MM-DD HH:MM" or timestamp
    stagger_minutes = int(data.get("stagger_minutes", 15)) # Leech gio giua cac page
    
    if not clip_filename:
        return jsonify({"error": "Thiếu tên file clip"}), 400
    
    video_path = OUTPUT_DIR / clip_filename
    if not video_path.exists():
        return jsonify({"error": f"Không tìm thấy file video: {clip_filename}"}), 404

    pages = page_manager.list_pages()
    groups = page_manager.list_groups()

    target_page_ids = []
    if page_id:
        target_page_ids.append(page_id)
    if page_ids and isinstance(page_ids, list):
        for pid in page_ids:
            if pid not in target_page_ids:
                target_page_ids.append(pid)
    if group_id:
        grp = next((g for g in groups if g.get("id") == group_id), None)
        if grp:
            for pid in grp.get("page_ids", []):
                if pid not in target_page_ids:
                    target_page_ids.append(pid)

    if not target_page_ids:
        return jsonify({"error": "Vui lòng chọn ít nhất 1 Fanpage hoặc 1 Nhóm Page để đăng"}), 400

    full_description = f"{title}\n\n{caption}".strip()
    results = []
    success_count = 0
    pages_updated = False

    # Tinh toan thoi gian hen gio co stagger cho tung page
    base_schedule_ts = None
    if schedule_time:
        try:
            s_str = str(schedule_time).strip().replace("T", " ")
            if len(s_str) == 16:
                s_str += ":00"
            dt = datetime.strptime(s_str[:19], "%Y-%m-%d %H:%M:%S")
            base_schedule_ts = int(dt.timestamp())
        except Exception:
            try:
                base_schedule_ts = int(schedule_time)
            except Exception:
                pass

    for idx, pid in enumerate(target_page_ids):
        p_info = next((p for p in pages if p.get("page_id") == pid), None)
        if not p_info:
            results.append({"page_id": pid, "success": False, "error": "Không tìm thấy thông tin Page"})
            continue

        p_token = p_info.get("page_token")
        if not p_token:
            results.append({"page_id": pid, "page_name": p_info.get("page_name"), "success": False, "error": "Chưa có Token hợp lệ"})
            continue

        # Tinh gio hen kem jitter/stagger cho page nay neu co schedule
        curr_sched = None
        if base_schedule_ts:
            curr_sched = base_schedule_ts + (idx * stagger_minutes * 60)

        res = reel_poster.publish_reel(
            page_id=pid,
            page_token=p_token,
            video_path=str(video_path),
            description=full_description,
            first_comment=first_comment,
            schedule_time=curr_sched
        )

        if res.get("success"):
            success_count += 1
            p_info["total_posted"] = p_info.get("total_posted", 0) + 1
            pages_updated = True
            results.append({
                "page_id": pid,
                "page_name": p_info.get("page_name"),
                "success": True,
                "status": res.get("status"),
                "video_id": res.get("video_id"),
                "scheduled_publish_time": res.get("scheduled_publish_time"),
                "comment_result": res.get("comment_result")
            })
        else:
            results.append({
                "page_id": pid,
                "page_name": p_info.get("page_name"),
                "success": False,
                "error": res.get("error")
            })

    if pages_updated:
        page_manager.save_pages(pages)

    return jsonify({
        "success": success_count > 0,
        "total_targets": len(target_page_ids),
        "success_count": success_count,
        "results": results
    })

@app.after_request
def _disable_html_cache(response):
    if response.mimetype == "text/html":
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# -------------------------------------------------------------
# Website Article CMS Config Routes
# -------------------------------------------------------------
WEBSITE_CFG_FILE = os.path.join(ROOT_DIR, "config", "website_config.json")

def load_website_config():
    if os.path.exists(WEBSITE_CFG_FILE):
        try:
            with open(WEBSITE_CFG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"base_url": "", "username": "", "password": "", "video_upload": {"method": "scp", "port": 22}}

def save_website_config(cfg):
    os.makedirs(os.path.dirname(WEBSITE_CFG_FILE), exist_ok=True)
    with open(WEBSITE_CFG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

@app.route("/api/website-config", methods=["GET"])
def api_get_website_config():
    cfg = load_website_config()
    return jsonify({
        "success": True,
        "config": {
            "base_url": cfg.get("base_url", ""),
            "username": cfg.get("username", ""),
            "has_password": bool(cfg.get("password")),
            "video_upload": cfg.get("video_upload") or {"method": "scp", "port": 22}
        }
    })

@app.route("/api/website-config", methods=["POST"])
def api_save_website_config():
    data = request.json or {}
    base_url = data.get("base_url", "").strip()
    username = data.get("username", "").strip()
    password = data.get("password", "")
    video_upload = data.get("video_upload")

    cfg = load_website_config()
    if base_url:
        cfg["base_url"] = base_url
    if username:
        cfg["username"] = username
    if password:
        cfg["password"] = password
    if isinstance(video_upload, dict):
        current_video = dict(cfg.get("video_upload") or {})
        for key in ("method", "host", "port", "username", "private_key_path", "remote_dir", "public_base_url"):
            if key in video_upload:
                current_video[key] = video_upload[key]
        cfg["video_upload"] = current_video

    save_website_config(cfg)
    return jsonify({"success": True, "message": "Đã lưu cấu hình website thành công"})

@app.route("/api/website-config/test", methods=["POST"])
def api_test_website_config():
    cfg = load_website_config()
    base_url = cfg.get("base_url", "").strip()
    if not base_url:
        return jsonify({"success": False, "error": "Chưa nhập Website URL"}), 400
    if not HAS_WEBSITE_SVC:
        return jsonify({"success": False, "error": "Bản cài thiếu WebsiteArticleService"}), 500
    try:
        result = WebsiteArticleService(WEBSITE_CFG_FILE).test_connection()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 502

@app.route("/api/website-config/test-video", methods=["POST"])
def api_test_video_uploader():
    if not HAS_WEBSITE_SVC:
        return jsonify({"success": False, "error": "Bản cài thiếu WebsiteArticleService"}), 500
    try:
        return jsonify(WebsiteArticleService(WEBSITE_CFG_FILE).test_video_uploader())
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 502



@app.route("/api/posts/clear", methods=["POST"])
def api_clear_posts():
    try:
        data = request.get_json(silent=True) or {}
        status_filter = data.get("status", "all") # 'all' or 'scheduled'
        
        posts = load_posts()
        if status_filter == "scheduled":
            new_posts = [p for p in posts if p.get("status") != "scheduled"]
            removed_count = len(posts) - len(new_posts)
        else:
            removed_count = len(posts)
            new_posts = []
            
        save_posts(new_posts)
        return jsonify({
            "success": True, 
            "removed_count": removed_count,
            "message": f"Đã hủy và xóa {removed_count} bài đăng thành công!"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "message": f"Lỗi: {str(e)}"}), 500

@app.route("/api/posts", methods=["GET"])
def api_get_posts():
    posts = load_posts()
    # Sắp xếp bài mới lên lịch / mới đăng lên đầu danh sách (Newest First)
    def _sort_key(p):
        # Ưu tiên sắp xếp theo thời điểm tạo bài hoặc lên lịch
        c_at = p.get("created_at", "")
        s_at = p.get("scheduled_time", "")
        p_id = p.get("id", "")
        return (c_at, s_at, p_id)
    posts = sorted(posts, key=_sort_key, reverse=True)
    return jsonify(posts)

@app.route("/api/posts", methods=["POST"])
def api_save_post():
    data = request.json or {}
    posts = load_posts()
    post_id = f"post_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    
    new_post = {
        "id": post_id,
        "title": data.get("title", ""),
        "content": data.get("content", ""),
        "hashtags": data.get("hashtags", ""),
        "page_id": data.get("page_id", ""),
        "page_name": data.get("page_name", ""),
        "group_id": data.get("group_id", ""),
        "group_name": data.get("group_name", ""),
        "type": data.get("type", "reel"),
        "media_file": data.get("media_file", ""),
        "first_comment": data.get("first_comment", ""),
        "status": data.get("status", "scheduled"),
        "scheduled_time": data.get("scheduled_time", ""),
        "posted_at": data.get("posted_at", ""),
        "url": data.get("url", ""),
        "token_name": data.get("token_name", "System User"),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "error_msg": data.get("error_msg", "")
    }
    posts.insert(0, new_post)
    save_posts(posts)
    return jsonify({"success": True, "post": new_post})

@app.route("/api/posts/<post_id>", methods=["DELETE"])
def api_delete_post(post_id):
    posts = load_posts()
    posts = [p for p in posts if p.get("id") != post_id]
    save_posts(posts)
    return jsonify({"success": True})


@app.route("/api/distribute/batch", methods=["POST"])
def api_distribute_batch():
    import re
    from datetime import datetime, timedelta
    data = request.json or {}
    group_id = data.get("group_id")
    clip_filenames = data.get("clip_filenames", [])
    posts_per_page = int(data.get("posts_per_page", 1))
    stagger_minutes = int(data.get("stagger_minutes", 15))
    auto_first_comment = data.get("auto_first_comment", True)
    use_llm_comment = data.get("use_llm_comment", True)

    if not group_id:
        return jsonify({"error": "Thiếu group_id"}), 400

    groups = page_manager.list_groups()
    group = next((g for g in groups if g.get("id") == group_id), None)
    if not group:
        return jsonify({"error": "Không tìm thấy Nhóm Fanpage"}), 404

    page_ids = group.get("page_ids", [])
    if not page_ids:
        return jsonify({"error": "Nhóm chưa có Fanpage nào được thêm"}), 400

    pages = page_manager.list_pages()
    page_map = {p["page_id"]: p for p in pages}
    posts = load_posts()

    resolved_page_tokens = {}
    missing_page_tokens = []
    for pid in page_ids:
        p_info = page_map.get(pid, {})
        page_token = str(p_info.get("page_token") or "").strip()
        if not page_token and p_info.get("token_id"):
            token_entry = token_vault.get_token_by_id(p_info.get("token_id")) or {}
            page_token = str(token_entry.get("token") or "").strip()
        if page_token:
            resolved_page_tokens[pid] = page_token
        else:
            missing_page_tokens.append(p_info.get("page_name") or str(pid))

    if missing_page_tokens:
        return jsonify({
            "error": "Các Page chưa có token đăng bài hợp lệ: " + ", ".join(missing_page_tokens)
        }), 400

    sched_cfg = group.get("schedule_config") or {}
    group_times = sched_cfg.get("times") or ["11:30", "19:30"]
    group_stagger = sched_cfg.get("stagger_minutes") or stagger_minutes

    folder_path = Path(group.get("folder_path") or group.get("folder_binding") or str(OUTPUT_DIR))
    if not folder_path.exists():
        folder_path = OUTPUT_DIR

    posted_file = BASE_DIR / "posted_clips.json"
    posted_set = set()
    if posted_file.exists():
        try:
            posted_set = set(json.loads(posted_file.read_text(encoding="utf-8")))
        except Exception:
            posted_set = set()

    queued_clips = {p.get("media_file") or p.get("clip_filename") for p in posts if p.get("status") in ["scheduled", "publishing"]}

    available_clips = []
    if clip_filenames:
        for fn in clip_filenames:
            if fn not in posted_set and fn not in queued_clips and (folder_path / fn).exists():
                available_clips.append(fn)
    else:
        for p in sorted(folder_path.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
            if p.name not in posted_set and p.name not in queued_clips:
                available_clips.append(p.name)

    if not available_clips:
        return jsonify({"error": "Không còn video clip mới nào chưa đăng/chưa hẹn để phân bổ! Hãy render thêm hoặc kiểm tra thư mục nguồn."}), 400

    now_ts = datetime.now()
    scheduled_count = 0
    assigned_clips = []
    clip_idx = 0

    for slot_idx in range(posts_per_page):
        time_str = group_times[slot_idx % len(group_times)]
        try:
            parts = time_str.strip().split(":")
            th = int(parts[0])
            tm = int(parts[1]) if len(parts) > 1 else 0
        except Exception:
            th, tm = 11, 30

        target_date = now_ts.date()
        slot_base_dt = datetime(target_date.year, target_date.month, target_date.day, th, tm, 0)
        if slot_base_dt <= now_ts:
            slot_base_dt += timedelta(days=1)

        for idx, pid in enumerate(page_ids):
            if clip_idx >= len(available_clips):
                break

            clip_fn = available_clips[clip_idx]
            clip_idx += 1

            p_info = page_map.get(pid, {})
            page_token = resolved_page_tokens[pid]

            post_id = f"post_{int(time.time())}_{uuid.uuid4().hex[:6]}"
            sched_dt = slot_base_dt + timedelta(minutes=(idx * group_stagger))
            sched_time_str = sched_dt.strftime("%Y-%m-%d %H:%M:%S")

            # Lấy thông tin video bám sát nội dung gốc
            meta = get_clip_metadata(clip_fn)
            video_title = meta.get("video_title") or meta.get("clean_title") or f"Highlight Moments #{scheduled_count+1}"

            post_entry = {
                "id": post_id,
                "title": f"{video_title.title()}",
                "content": f"Watch the thrilling highlights & full breakdown! Check the official footage link in the first comment below.\n#reels #trending #highlight #viral #sports",
                "hashtags": "#reels #trending #highlight #viral #sports",
                "page_id": pid,
                "page_name": p_info.get("page_name", f"Fanpage {pid}"),
                "group_id": group_id,
                "group_name": group.get("name", "Nhóm Fanpage"),
                "type": "reel",
                "media_file": clip_fn,
                "article_url": "",
                "first_comment": "",
                "auto_first_comment": bool(auto_first_comment),
                "use_llm_comment": bool(use_llm_comment),
                "status": "scheduled",
                "scheduled_time": sched_time_str,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "token": page_token
            }
            posts.append(post_entry)
            assigned_clips.append(clip_fn)
            scheduled_count += 1

    save_posts(posts)
    return jsonify({
        "success": True,
        "scheduled_count": scheduled_count,
        "posts_per_page": posts_per_page,
        "message": f"Đã phân bổ thành công {scheduled_count} bài viết cho {len(page_ids)} Fanpage ({posts_per_page} bài/page)!"
    })

SCHEDULE_RULES_FILE = BASE_DIR / "config" / "schedule_rules.json"

def get_schedule_rules():
    if not SCHEDULE_RULES_FILE.exists():
        return {
            "slots": ["07:00", "11:30", "17:00", "20:00"],
            "stagger_minutes": 15,
            "posts_per_day": 4,
            "auto_first_comment": True
        }
    try:
        import json
        return json.loads(SCHEDULE_RULES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {
            "slots": ["07:00", "11:30", "17:00", "20:00"],
            "stagger_minutes": 15,
            "posts_per_day": 4,
            "auto_first_comment": True
        }

def save_schedule_rules(rules):
    try:
        import json
        SCHEDULE_RULES_FILE.parent.mkdir(parents=True, exist_ok=True)
        SCHEDULE_RULES_FILE.write_text(json.dumps(rules, indent=2, ensure_ascii=False), encoding="utf-8")
        return rules
    except Exception:
        return rules

@app.route("/api/schedule/rules", methods=["GET", "POST"])
def handle_schedule_rules():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        saved = save_schedule_rules(data)
        return jsonify({"status": "ok", "rules": saved})
    return jsonify({"status": "ok", "rules": get_schedule_rules()})



@app.route("/api/tokens/recommend", methods=["GET"])
def api_recommend_tokens():
    page_count = int(request.args.get("pages", 30))
    rec = token_vault.auto_balance_group(page_count)
    return jsonify({"success": True, "recommendation": rec})

@app.route("/api/tokens/health", methods=["GET"])
def api_tokens_health():
    tokens = token_vault.list_tokens(mask=True)
    stats = {
        "total": len(tokens),
        "active": sum(1 for t in tokens if t.get("status") == "ACTIVE"),
        "healthy": sum(1 for t in tokens if t.get("rate_status") == "NORMAL" and t.get("status") == "ACTIVE"),
        "warning_60": sum(1 for t in tokens if t.get("rate_status") == "WARNING_60"),
        "cooldown_80": sum(1 for t in tokens if t.get("rate_status") == "COOLDOWN_80"),
        "tokens": tokens
    }
    return jsonify({"success": True, "data": stats})

@app.route("/api/queue/status", methods=["GET"])
def api_queue_status():
    all_jobs = load_jobs()
    queued_count = sum(1 for j in all_jobs if j.get("status") == "queued")
    running_count = sum(1 for j in all_jobs if j.get("status") == "running")
    completed_count = sum(1 for j in all_jobs if j.get("status") == "completed")
    error_count = sum(1 for j in all_jobs if j.get("status") == "error")
    return jsonify({
        "is_paused": IS_QUEUE_PAUSED,
        "max_concurrent": MAX_CONCURRENT_JOBS,
        "queued": queued_count,
        "running": running_count,
        "completed": completed_count,
        "error": error_count,
        "total": len(all_jobs)
    })

@app.route("/api/queue/pause", methods=["POST"])
def api_queue_pause():
    global IS_QUEUE_PAUSED
    IS_QUEUE_PAUSED = True
    return jsonify({"success": True, "is_paused": True, "message": "Đã tạm dừng nhận link mới từ hàng đợi."})

@app.route("/api/queue/resume", methods=["POST"])
def api_queue_resume():
    global IS_QUEUE_PAUSED
    IS_QUEUE_PAUSED = False
    return jsonify({"success": True, "is_paused": False, "message": "Đã tiếp tục xử lý hàng đợi."})

@app.route("/api/queue/clear", methods=["POST"])
def api_queue_clear():
    jobs = load_jobs()
    cancelled_count = 0
    for j in jobs:
        if j.get("status") == "queued":
            j["status"] = "cancelled"
            j["progress_msg"] = "Đã hủy bởi người dùng"
            CANCELLED_JOB_IDS.add(j["id"])
            cancelled_count += 1
    save_jobs(jobs)
    return jsonify({"success": True, "cancelled_count": cancelled_count, "message": f"Đã hủy {cancelled_count} jobs đang chờ."})

@app.route("/api/jobs/<job_id>/cancel", methods=["POST"])
def api_job_cancel(job_id):
    jobs = load_jobs()
    found = False
    for j in jobs:
        if j.get("id") == job_id:
            j["status"] = "cancelled"
            j["progress_msg"] = "Đã dừng/hủy tiến trình"
            CANCELLED_JOB_IDS.add(job_id)
            found = True
            break
    if found:
        save_jobs(jobs)
        return jsonify({"success": True, "message": f"Đã hủy job {job_id}"})
    return jsonify({"error": "Job không tồn tại"}), 404


@app.route("/api/pages/update_binding", methods=["POST"])
def api_update_page_binding():
    data = request.json or {}
    page_id = str(data.get("page_id", "")).strip()
    group_id = str(data.get("group_id", "")).strip()
    token_id = str(data.get("token_id", "")).strip()

    if not page_id:
        return jsonify({"success": False, "error": "Thiếu page_id"}), 400

    pages = page_manager.list_pages()
    groups = page_manager.list_groups()
    tokens = token_vault.list_tokens(mask=False)

    target_page = next((p for p in pages if str(p.get("page_id") or p.get("id")) == page_id), None)
    if not target_page:
        return jsonify({"success": False, "error": "Không tìm thấy Fanpage"}), 404

    # 1. Cập nhật nhóm
    if group_id:
        matched_grp = next((g for g in groups if g.get("id") == group_id or g.get("name") == group_id), None)
        if matched_grp:
            target_page["group_ids"] = [matched_grp.get("id")]
            target_page["group_name"] = matched_grp.get("name")
            # Cập nhật page_id vào group nếu chưa có
            p_ids = matched_grp.get("page_ids", [])
            if page_id not in p_ids:
                p_ids.append(page_id)
                matched_grp["page_ids"] = p_ids
                page_manager.save_groups(groups)
    else:
        target_page["group_ids"] = []
        target_page["group_name"] = "Chưa nhóm"

    # 2. Cập nhật token
    if token_id:
        matched_tok = next((t for t in tokens if str(t.get("id")) == token_id), None)
        if matched_tok:
            target_page["token_id"] = token_id
            target_page["token_name"] = matched_tok.get("name", "System User")
            if matched_tok.get("token"):
                target_page["page_token"] = matched_tok.get("token")
    else:
        target_page["token_id"] = ""
        target_page["token_name"] = "AutoPool (Tự động)"

    page_manager.save_pages(pages)
    return jsonify({
        "success": True, 
        "message": f"Đã cập nhật Nhóm '{target_page.get('group_name')}' & Token '{target_page.get('token_name')}' cho trang {target_page.get('page_name')}!"
    })


@app.route("/api/pages/assign_token", methods=["POST"])
def api_assign_token():
    data = request.json or {}
    page_id = str(data.get("page_id", ""))
    token_id = str(data.get("token_id", ""))
    
    if not page_id:
        return jsonify({"error": "Thiếu page_id"}), 400
        
    pages = page_manager.list_pages()
    updated = False
    for p in pages:
        if str(p.get("page_id")) == page_id:
            p["token_id"] = token_id
            updated = True
            break
            
    if updated:
        page_manager.save_pages(pages)
        return jsonify({"success": True, "message": f"Đã gán Token {token_id} cho Page {page_id}"})
    return jsonify({"error": "Không tìm thấy Page"}), 404

@app.route("/api/pages/batch_assign_token", methods=["POST"])
def api_batch_assign_token():
    data = request.json or {}
    pages = page_manager.list_pages()
    count = 0

    # 1. Hỗ trợ dạng mảng gán chi tiết từng page (round-robin assignments)
    assignments = data.get("assignments")
    if isinstance(assignments, list) and assignments:
        assign_map = {str(a.get("page_id")): str(a.get("token_id")) for a in assignments if a.get("page_id") and a.get("token_id")}
        for p in pages:
            pid = str(p.get("page_id"))
            if pid in assign_map:
                p["token_id"] = assign_map[pid]
                count += 1
        page_manager.save_pages(pages)
        return jsonify({"success": True, "count": count, "message": f"Đã tự động xoay vòng chia đều token cho {count} trang."})

    # 2. Hỗ trợ dạng gán 1 token_id cho danh sách page_ids
    token_id = str(data.get("token_id", ""))
    page_ids = [str(pid) for pid in data.get("page_ids", [])]
    if not token_id:
        return jsonify({"error": "Thiếu token_id hoặc danh sách phân bổ assignments"}), 400

    for p in pages:
        if str(p.get("page_id")) in page_ids:
            p["token_id"] = token_id
            count += 1

    page_manager.save_pages(pages)
    return jsonify({"success": True, "count": count, "message": f"Đã gán cứng Token cho {count} trang."})


@app.route("/api/clips/purge_posted", methods=["POST"])
def api_purge_posted_clips():
    """
    Xóa tất cả các video clip đã được đánh dấu 'is_posted' hoặc đã đưa vào lịch thành công
    giúp giải phóng dung lượng ổ D và chống đăng trùng video.
    """
    posted_file = BASE_DIR / "posted_clips.json"
    if not posted_file.exists():
        return jsonify({"success": True, "deleted_count": 0, "freed_mb": 0, "message": "Chưa có clip nào được đánh dấu đã đăng."})
    
    try:
        posted_data = json.loads(posted_file.read_text(encoding="utf-8"))
    except Exception:
        posted_data = []

    if not posted_data:
        return jsonify({"success": True, "deleted_count": 0, "freed_mb": 0, "message": "Danh sách đã đăng rỗng."})

    deleted_count = 0
    total_freed_bytes = 0
    jobs = load_jobs()
    jobs_updated = False

    for fn in posted_data:
        file_path = OUTPUT_DIR / fn
        if file_path.exists():
            try:
                total_freed_bytes += file_path.stat().st_size
                file_path.unlink()
                deleted_count += 1
            except Exception as err:
                print(f"[Purge] Error deleting {fn}: {err}")

        # Đồng bộ xoá khỏi jobs.json
        for j in jobs:
            clips = j.get("clips", [])
            new_clips = [c for c in clips if c.get("filename") != fn]
            if len(new_clips) != len(clips):
                j["clips"] = new_clips
                jobs_updated = True

    if jobs_updated:
        save_jobs(jobs)

    freed_mb = round(total_freed_bytes / (1024 * 1024), 2)
    return jsonify({
        "success": True,
        "deleted_count": deleted_count,
        "freed_mb": freed_mb,
        "message": f"Đã xóa thành công {deleted_count} video đã dùng, giải phóng {freed_mb} MB trên ổ D!"
    })

@app.route("/api/website/publish_draft", methods=["POST"])
def api_publish_website_article():
    """
    Tạo bài viết web kèm video dài trực tiếp (không link ngoài) và ảnh hook gây tò mò.
    Sinh link chính thức để đưa vào First Comment kéo traffic về web.
    """
    data = request.json or {}
    title = data.get("title", "").strip()
    summary = data.get("summary", "").strip()
    hook_img = data.get("hook_image", "") # đường dẫn hoặc URL ảnh hook
    long_video = data.get("video_path", "")
    dry_run = data.get("dry_run", False)

    if not title:
        return jsonify({"success": False, "error": "Thiếu tiêu đề bài viết"}), 400

    cfg_file = BASE_DIR / "config" / "website_config.json"
    if not HAS_WEBSITE_SVC:
        return jsonify({"success": False, "error": "Bản cài thiếu WebsiteArticleService"}), 500

    try:
        svc = WebsiteArticleService(str(cfg_file))
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    # Chỉ chấp nhận URL HTTPS đã xác minh hoặc file nằm trong downloads/output.
    public_video_url = ""
    local_video_path = None
    if str(long_video).startswith("https://"):
        try:
            svc.verify_public_media(long_video, require_range=True)
            public_video_url = long_video
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 400
    else:
        requested_name = Path(str(long_video).replace("\\", "/")).name
        candidates = []
        if long_video:
            raw_path = Path(long_video)
            if raw_path.is_absolute():
                candidates.append(raw_path)
        candidates.extend([OUTPUT_DIR / requested_name, DOWNLOADS_DIR / requested_name])
        allowed_roots = [OUTPUT_DIR.resolve(), DOWNLOADS_DIR.resolve()]
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
                if resolved.is_file() and any(root == resolved.parent or root in resolved.parents for root in allowed_roots):
                    local_video_path = resolved
                    break
            except Exception:
                continue
        if not local_video_path:
            return jsonify({"success": False, "error": "Không tìm thấy video local hợp lệ để upload"}), 400
        try:
            public_video_url = svc.upload_video(str(local_video_path))
        except Exception as exc:
            return jsonify({"success": False, "error": f"Upload video thất bại: {exc}"}), 502

    safe_title = html.escape(title)
    safe_summary = html.escape(summary or title)
    safe_video_url = html.escape(public_video_url, quote=True)
    safe_hook_url = html.escape(hook_img, quote=True) if str(hook_img).startswith("https://") else ""
    body_html = f"""
    <div class="article-content">
      <p class="lead-summary"><strong>{safe_summary}</strong></p>
      <div class="video-container" style="margin: 20px 0; text-align: center;">
        <video controls playsinline preload="metadata" style="width: 100%; max-width: 720px; border-radius: 8px; background: #000;" poster="{safe_hook_url}">
          <source src="{safe_video_url}" type="video/mp4">
          Trình duyệt của bạn không hỗ trợ phát video trực tiếp.
        </video>
      </div>
      <p>Xem toàn bộ diễn biến chi tiết và cập nhật mới nhất ở trên.</p>
    </div>
    """

    slug = re.sub(r'[^a-zA-Z0-9]+', '-', title.lower()).strip('-')[:60]
    try:
        res = svc.publish_article(
            title=title,
            slug=slug,
            body_html=body_html,
            image_path=hook_img if hook_img and os.path.exists(hook_img) else None,
            image_url=hook_img if str(hook_img).startswith("https://") else "",
            dry_run=dry_run,
        )
        article_url = res.get("article_url")
        if not article_url:
            raise WebsiteServiceError("CMS không trả article_url")
    except Exception as exc:
        return jsonify({"success": False, "error": f"Đăng bài CMS thất bại: {exc}"}), 502

    # First comment kích thích tò mò có kèm ảnh hook & link web
    try:
        from src.publisher.website_publisher import generate_curiosity_comment_with_llm
        first_comment = generate_curiosity_comment_with_llm(title, article_url, enable_llm=True)
    except Exception as _efc:
        first_comment = f"🔥 Watch the full uncut footage and breakdown here: {article_url}\n👉 Scroll down the article to stream the complete high-definition video!"

    return jsonify({
        "success": True,
        "article_url": article_url,
        "first_comment": first_comment,
        "hook_image": hook_img,
        "title": title,
        "video_url": public_video_url,
        "cms_verified": not dry_run,
    })


if __name__ == "__main__":
    import waitress
    print("Highlight Video Studio starting on port 5080 with Waitress (threads=8)...")
    waitress.serve(app, host="0.0.0.0", port=5080, threads=8, channel_timeout=30)
