import sys
from pathlib import Path

# The scheduled queue lives under one canonical root per installation; a packaged
# and a dev launch must not read/write different posts.json files.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from multi_pc.data_root import canonical_data_root  # noqa: E402

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
import re
import requests
from urllib.parse import urlparse
import uuid
import threading
from queue import Queue
import time

from multi_pc.concurrency import (
    HARD_MAX_CONCURRENT_RENDERS,
    bounded_concurrency,
    resolve_concurrency,
)
from multi_pc.json_io import replace_with_retry
from multi_pc.posting_schedule import paced_offsets_by_token, posting_schedule_recommendation
from datetime import datetime, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
# Mutable state (queue, tokens, pages, output) must resolve to one root so a
# reloader or packaged entrypoint cannot split scheduled posts across files.
DATA_ROOT = canonical_data_root(allow_repo_fallback=ROOT_DIR)
if str(DATA_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_ROOT))
os.chdir(str(DATA_ROOT))

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
    extract_youtube_video_id,
    build_youtube_embed_html,
)
from src.publisher.meta_reel_poster import MetaReelPoster
from src.publisher.meta_preflight import (
    preflight_pages,
    resolve_page_token,
)
from src.first_comment_profiles import (
    builtin_profiles,
    load_profile_store,
    normalize_profile,
    save_profile_store,
)
from src.llm_response import chat_text_from_response, chat_model_unavailable, chat_stream_incomplete
from core.text_encoding import repair_mojibake


app = Flask(__name__, template_folder="templates", static_folder="static")

# This build identity is kept in code because upgrades intentionally preserve
# the user's config.json, whose version field can therefore be missing/stale.
APP_VERSION = "1.1.9"

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


BASE_DIR = DATA_ROOT
DOWNLOADS_DIR = DATA_ROOT / "downloads"
OUTPUT_DIR = DATA_ROOT / "output"
TEMP_DIR = DATA_ROOT / "temp"
JOBS_FILE = DATA_ROOT / "jobs.json"
POSTS_FILE = DATA_ROOT / "posts.json"
CRAWLED_VIDEOS_FILE = DATA_ROOT / "crawled_videos.json"
FIRST_COMMENT_PROFILES_FILE = DATA_ROOT / "data" / "first_comment_profiles.json"


def prioritize_scheduled_packages(package_ids):
    """Move newly scheduled work ahead of unscheduled library backlog.

    The content worker claims the first queued row under this same lock. An
    already-running CMS/LLM call cannot be interrupted, but subsequent claims
    process scheduled rows first without blocking the schedule HTTP response.
    """
    from src import content_packages as packages

    wanted = set(package_ids)
    if not wanted:
        return
    with packages._LOCK:
        items = packages._read(packages.QUEUE_FILE, [])
        changed = False
        for item in items:
            if item.get("id") in wanted and item.get("status") == "queued":
                item["schedule_priority"] = True
                changed = True
        if changed:
            items.sort(key=lambda item: 0 if item.get("schedule_priority") and item.get("status") == "queued" else 1)
            packages._write(packages.QUEUE_FILE, items)


def prepare_website_article_for_schedule(
    clip_filename,
    title,
    *,
    article_url="",
    first_comment="",
    auto_first_comment=True,
    use_llm_comment=True,
):
    """Create website content before a schedule is acknowledged.

    Website failures are returned as schedule metadata instead of raising, so a
    valid Facebook schedule is never dropped because CMS upload/publish failed.
    """
    article_url = str(article_url or "").strip()
    first_comment = str(first_comment or "").strip()
    result = {
        "article_url": article_url,
        "website_status": "ready" if article_url else "not_configured",
        "website_error": "",
        "first_comment": first_comment,
        "first_comment_status": "ready" if first_comment else "not_configured",
        "first_comment_error": "",
    }
    if not auto_first_comment:
        return result
    try:
        if not article_url:
            cms_result = publish_clip_to_website_cms(clip_filename, title)
            article_url = cms_result[0] if isinstance(cms_result, tuple) else str(cms_result or "")
            if not article_url:
                raise WebsiteServiceError("CMS không trả Website URL")
        if not first_comment:
            try:
                first_comment = generate_curiosity_comment_with_llm(
                    title,
                    article_url,
                    enable_llm=bool(use_llm_comment),
                )
            except Exception:
                first_comment = (
                    f"🔥 Watch the full uncut footage and breakdown here: {article_url}\n"
                    "👉 Scroll down the article to stream the complete high-definition video!"
                )
        result.update({
            "article_url": article_url,
            "website_status": "ready",
            "website_error": "",
            "first_comment": first_comment,
            "first_comment_status": "ready" if first_comment else "not_configured",
            "first_comment_error": "",
        })
    except Exception as exc:
        error = str(exc)
        result.update({
            "website_status": "failed",
            "website_error": error,
            "first_comment_status": "generation_failed" if not first_comment else "ready",
            "first_comment_error": error if not first_comment else "",
        })
    return result

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

try:
    from web.posts_store import load_posts_file, save_posts_file
except ImportError:
    from posts_store import load_posts_file, save_posts_file


def load_posts():
    return load_posts_file(POSTS_FILE)


def save_posts(posts):
    save_posts_file(POSTS_FILE, posts)


for d in [DOWNLOADS_DIR, OUTPUT_DIR, TEMP_DIR]:
    d.mkdir(parents=True, exist_ok=True)

token_vault = TokenVault(BASE_DIR)
page_manager = PageManager(BASE_DIR)
reel_poster = MetaReelPoster(token_vault=token_vault)
from web.page_insights import PageInsightsService
page_insights_service = PageInsightsService(BASE_DIR, token_vault, page_manager)


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
            replace_with_retry(tmp_file, JOBS_FILE)
            return True
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
        now = datetime.now().isoformat(timespec="seconds")
        update_job_status(job_id, {
            "status": status,
            "step": step,
            "progress_msg": msg,
            "heartbeat_at": now,
            "updated_at": now,
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
            update_msg("Không tìm thấy subtitle YouTube, khởi chạy Whisper với tự động chọn CUDA/CPU...", step=2)
            segments = transcribe_local_whisper(
                audio_path,
                update_status=lambda message: update_msg(message, step=2),
            )

        if not segments:
            raise RuntimeError("Không thể lấy phụ đề hoặc nhận diện giọng nói của video này.")

        # Bước 3: AI LLM phân tích Hook & Highlight
        update_msg("AI Gemini đang phân tích nội dung, chấm điểm Viral & cắt Hook...", step=3)
        highlights = ask_llm_for_highlights(segments, num_clips=num_clips, target_length=job.get("clip_length", "auto"), criteria=job.get("highlight_criteria", "hook_viral"), hook_duration=job.get("hook_duration", 6), update_status=lambda m: update_msg(m, step=3))
        if not highlights:
            raise RuntimeError("AI không thể tìm thấy đoạn highlight phù hợp.")

        # Bước 4 & 5: Smart Reframe & Render từng clip (kèm Dynamic Subtitle)
        update_msg(f"Bắt đầu render {len(highlights)} clips highlight 9:16 (encoder tự động, tối đa {MAX_CONCURRENT_JOBS} job)...", step=4)
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

        now = datetime.now().isoformat(timespec="seconds")
        update_job_status(job_id, {
            "status": "completed",
            "step": 5,
            "progress_msg": f"Hoàn tất! Đã xuất {len(rendered_clips)} clips highlight chất lượng cao.",
            "clips": rendered_clips,
            "heartbeat_at": now,
            "updated_at": now,
            "finished_at": now,
        })

    except Exception as e:
        now = datetime.now().isoformat(timespec="seconds")
        update_job_status(job_id, {
            "status": "error",
            "progress_msg": f"Lỗi xử lý: {str(e)}",
            "error": str(e),
            "heartbeat_at": now,
            "updated_at": now,
            "finished_at": now,
        })


# ==========================================
# BACKGROUND QUEUE MANAGER FOR BATCH RENDERING
# ==========================================
# The startup profiler writes this value before this module is imported.
def _profile_concurrency_default():
    profile_path = BASE_DIR / "data" / "hardware_profile.json"
    try:
        payload = json.loads(profile_path.read_text(encoding="utf-8"))
        profile = payload.get("profile") if isinstance(payload, dict) else {}
        value = profile.get("max_concurrent_renders", profile.get("concurrency", 1))
        return max(1, min(4, int(value)))
    except (OSError, ValueError, TypeError):
        return 1


AUTO_CONCURRENT_JOBS = max(1, min(
    HARD_MAX_CONCURRENT_RENDERS,
    int(os.environ.get("HIGHLIGHT_MAX_CONCURRENT_RENDERS", str(_profile_concurrency_default()))),
))
# Keep the existing profile/env default as Auto. A manual choice is runtime-only,
# bounded, and never changes the encoder or the persisted hardware profile.
CONCURRENCY_MODE = "auto"
MAX_CONCURRENT_JOBS = AUTO_CONCURRENT_JOBS
JOB_QUEUE = Queue()
ACTIVE_JOB_IDS = set()
CANCELLED_JOB_IDS = set()
RENDER_QUEUE_STATE_FILE = DATA_ROOT / "data" / "render_queue_state.json"


def load_render_queue_pause():
    try:
        return json.loads(RENDER_QUEUE_STATE_FILE.read_text(encoding="utf-8")).get("is_paused") is True
    except (OSError, ValueError, AttributeError):
        return False


def set_render_queue_pause(paused):
    global IS_QUEUE_PAUSED
    with QUEUE_LOCK:
        RENDER_QUEUE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        temporary = RENDER_QUEUE_STATE_FILE.with_name(f"render_queue_state.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_text(json.dumps({"is_paused": bool(paused)}), encoding="utf-8")
            replace_with_retry(temporary, RENDER_QUEUE_STATE_FILE)
        finally:
            temporary.unlink(missing_ok=True)
        IS_QUEUE_PAUSED = bool(paused)


IS_QUEUE_PAUSED = load_render_queue_pause()
QUEUE_LOCK = threading.Lock()


def recover_interrupted_jobs():
    """Requeue jobs left in running state after an app/process restart."""
    with JOBS_LOCK:
        jobs = load_jobs()
        changed = False
        now = datetime.now().isoformat(timespec="seconds")
        for job in jobs:
            if job.get("status") != "running":
                continue
            job["status"] = "queued"
            job["progress_msg"] = "Render bị gián đoạn khi ứng dụng khởi động lại; đã đưa lại vào hàng đợi."
            job["updated_at"] = now
            job["heartbeat_at"] = now
            job["recovered_at"] = now
            job["attempt"] = int(job.get("attempt", 0)) + 1
            changed = True
        if changed:
            save_jobs(jobs)
        return sum(1 for job in jobs if job.get("recovered_at") == now)


recover_interrupted_jobs()


def queue_worker_loop():
    global IS_QUEUE_PAUSED
    while True:
        try:
            if IS_QUEUE_PAUSED:
                time.sleep(2)
                continue
                
            with QUEUE_LOCK:
                at_capacity = len(ACTIVE_JOB_IDS) >= MAX_CONCURRENT_JOBS
            # Never sleep while holding QUEUE_LOCK: worker cleanup needs it to
            # release completed slots, otherwise the queue can remain stuck.
            if at_capacity:
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
    from web.scheduled_publisher import start_worker_thread, worker_status
except ImportError:
    from scheduled_publisher import start_worker_thread, worker_status
_publisher_thread = start_worker_thread()

@app.route("/")
def index():
    return render_template("index.html", app_version=APP_VERSION)

@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    return jsonify(repair_mojibake(load_jobs()))

@app.route("/api/jobs/<job_id>", methods=["GET"])
def get_job(job_id):
    jobs = load_jobs()
    for j in jobs:
        if j["id"] == job_id:
            return jsonify(repair_mojibake(j))
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
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "attempt": 0,
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
                
    return jsonify(repair_mojibake(all_clips))

@app.route("/api/clips/play/<path:filename>")
def play_clip(filename):
    safe_name = Path(str(filename).replace("\\", "/")).name
    if safe_name != filename or not safe_name.lower().endswith(".mp4"):
        return jsonify({"error": "Tên video không hợp lệ"}), 400
    target = (OUTPUT_DIR / safe_name).resolve()
    if target.parent != OUTPUT_DIR.resolve() or not target.is_file():
        return jsonify({"error": "Không tìm thấy video"}), 404
    return send_from_directory(
        str(OUTPUT_DIR), safe_name,
        as_attachment=request.args.get("download") == "1",
        conditional=True,
    )


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
        exact = _normalise_http_url(models_url, "Endpoint lấy model ảnh")
        path_only = exact.split("?", 1)[0]
        lower_path = path_only.lower()
        # Recover from the common mistake of pasting a POST generation endpoint
        # into the GET model-list field. This otherwise returns an opaque 405.
        for suffix in ("/images/generations", "/chat/completions"):
            if lower_path.endswith(suffix):
                return [path_only[:-len(suffix)] + "/models"]
        return [exact]
    return _llm_model_urls(api_base)


def _image_generation_candidates(generation_url="", api_base=""):
    """Return only the OpenAI-compatible image-generation endpoint."""
    exact = str(generation_url or "").strip()
    if exact:
        url = _normalise_http_url(exact, "Endpoint tạo ảnh")
        path = url.lower().split("?", 1)[0]
        if not path.endswith("/v1/images/generations"):
            raise ValueError("Endpoint tạo ảnh phải kết thúc bằng /v1/images/generations")
        return [(url, "images")]
    base = _normalise_llm_base(api_base)
    if not base.lower().endswith("/v1"):
        raise ValueError("API base tạo ảnh phải kết thúc bằng /v1, hoặc nhập URL đầy đủ /v1/images/generations")
    return [(f"{base}/images/generations", "images")]


def _image_test_payload(model, endpoint_type="images"):
    return {
        "model": model,
        "prompt": "A simple blue circle on white background",
        "n": 1,
        "size": "auto",
        "quality": "auto",
        "background": "auto",
        "image_detail": "high",
        "output_format": "png",
    }


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

def _as_dict(value):
    """Normalise a cached JSON fragment; tolerate missing/None/wrong types."""
    return value if isinstance(value, dict) else {}


def detect_hardware():
    """Return cached, ffprobe-validated hardware facts without blocking the UI."""
    import platform

    profile_path = BASE_DIR / "data" / "hardware_profile.json"
    try:
        entry = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        entry = {}
    entry = _as_dict(entry)
    hardware = _as_dict(entry.get("hardware"))
    profile = _as_dict(entry.get("profile"))
    canaries = _as_dict(entry.get("canaries"))
    gpu = _as_dict(hardware.get("gpu"))
    return {
        "hostname": platform.node(),
        "cpu": hardware.get("cpu_model") or platform.processor() or "x86_64 Processor",
        "cpu_logical_cores": hardware.get("cpu_logical_cores", os.cpu_count() or 1),
        "cpu_physical_cores": hardware.get("cpu_physical_cores", 0),
        "ram_mb": hardware.get("ram_mb", 0),
        "disk_free_mb": hardware.get("disk_free_mb", 0),
        "disk_write_mbps": hardware.get("disk_write_mbps", 0),
        "gpu": gpu.get("model") or "Unknown GPU",
        "gpu_vendor": gpu.get("vendor") or "unknown",
        "vram_mb": gpu.get("vram_mb", 0),
        "driver_version": gpu.get("driver_version") or "",
        "recommended_encoder": profile.get("codec") or "libx264",
        "render_profile": profile,
        "canaries": canaries,
        "profile_saved_at": entry.get("saved_at"),
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
            return jsonify({"success": False, "error": r"Không tìm thấy Google Chrome tại C:\Program Files\Google\Chrome\Application\chrome.exe"}), 404
            
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
        "app_version": APP_VERSION,
        "hardware": hw,
        "config": public_config(cfg)
    })


@app.route("/api/dashboard/summary", methods=["GET"])
def api_dashboard_summary():
    """Return live, non-secret overview data for the home dashboard."""
    from web.dashboard import overview
    try:
        pages = page_manager.list_pages()
        tokens = token_vault.list_tokens(mask=True)
        groups = page_manager.list_groups()
        jobs = load_jobs()
        data = overview(load_posts(), pages, tokens, groups, jobs)
        data["insights"] = page_insights_service.summary(pages)
        data["mapping_health"] = page_manager.mapping_health()
        from multi_pc.publishing_settings import load_publishing_settings
        data.update(load_publishing_settings(POSTS_FILE.parent))
        data["updated_at"] = datetime.now().astimezone().isoformat()
        try:
            from web.scheduled_publisher import worker_status
            data["scheduler"] = worker_status()
        except Exception:
            data["scheduler"] = {"thread_alive": False, "last_cycle_ok": False}
        data["render"] = {"is_paused": IS_QUEUE_PAUSED, "active": len(ACTIVE_JOB_IDS),
                           "running": sum(1 for job in jobs if job.get("status") == "running"),
                           "queued": sum(1 for job in jobs if job.get("status") == "queued")}
        data["success"] = True
        return jsonify(data)
    except Exception as exc:
        try:
            from web.scheduled_publisher import sanitize_error
            message = sanitize_error(exc)
        except Exception:
            message = "Không đọc được dữ liệu tổng quan."
        return jsonify({"success": False, "error": message}), 500


@app.route("/api/dashboard/insights", methods=["GET"])
def api_dashboard_insights():
    pages = page_manager.list_pages()
    page_id = str(request.args.get("page_id") or "").strip()
    if page_id and not any(str(page.get("page_id")) == page_id for page in pages):
        return jsonify({"success": False, "error": "Không tìm thấy Page."}), 404
    return jsonify({"success": True, "insights": page_insights_service.summary(pages, page_id)})


@app.route("/api/dashboard/insights/sync", methods=["POST"])
def api_dashboard_insights_sync():
    body = request.get_json(silent=True) or {}
    if not isinstance(body, dict):
        return jsonify({"success": False, "error": "Yêu cầu đồng bộ không hợp lệ."}), 400
    page_id = body.get("page_id") or ""
    if not isinstance(page_id, str):
        return jsonify({"success": False, "error": "Page ID không hợp lệ."}), 400
    try:
        progress = page_insights_service.start_sync(page_manager.list_pages(), page_id.strip())
        return jsonify({"success": True, "progress": progress}), 202 if progress.get("running") else 200
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 404

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
    selected_model = str(data.get("model") or image_cfg.get("model") or "").strip()
    if not selected_model or selected_model == "__video_frame__":
        return jsonify({"success": False, "error": "Vui lòng bật chế độ AI tạo ảnh"}), 400
    model = selected_model
    try:
        candidates = _image_generation_candidates(generation_url, raw_base)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    from web.scheduled_publisher import sanitize_error
    failures = []
    started = time.perf_counter()
    for url, endpoint_type in candidates:
        request_type = "images"
        try:
            response = requests.post(url, headers=_llm_headers(api_key), json=_image_test_payload(model), timeout=120)
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
            failures.append(f"HTTP {response.status_code} - {sanitize_error(detail)}")
        except requests.RequestException as exc:
            failures.append(sanitize_error(exc))
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
        if chat_model_unavailable(response):
            return jsonify({"success": False, "error": "Model Text LLM đã ngừng hoạt động trên endpoint này; hãy chọn model khác.",
                            "latency_ms": latency_ms}), 502
        if chat_stream_incomplete(response):
            return jsonify({"success": False, "error": "Provider trả luồng chat chưa hoàn tất; hãy thử lại hoặc chọn model khác.",
                            "latency_ms": latency_ms}), 502
        content = chat_text_from_response(response)
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
        
    try:
        res = generate_viral_content(
            title=title, summary=summary, hook=hook,
            video_url=video_url, comment_model=comment_model,
        )
    except Exception as exc:
        return jsonify({"success": False, "error": sanitize_error(exc) if isinstance(exc, (RuntimeError, ValueError)) else type(exc).__name__}), 502
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
_token_group_lock = threading.RLock()

def load_token_groups():
    if not TOKEN_GROUPS_FILE.exists():
        return []
    try:
        with open(TOKEN_GROUPS_FILE, "r", encoding="utf-8") as f:
            groups = json.load(f)
            if not isinstance(groups, list) or any(not isinstance(g, dict) for g in groups):
                raise ValueError("Token groups must be an array of group records")
            return groups
    except Exception as exc:
        raise RuntimeError("Không đọc được nhóm Token; giữ dữ liệu hiện có và khôi phục file nhóm.") from exc

def save_token_groups(groups):
    tmp = TOKEN_GROUPS_FILE.with_name(f".{TOKEN_GROUPS_FILE.name}.{uuid.uuid4().hex}.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(groups, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    replace_with_retry(tmp, TOKEN_GROUPS_FILE)


def sync_linked_page_group(group):
    """The token group's Page set is available in the posting group selector."""
    if not group.get("page_group_id"):
        group["page_group_id"] = f"grp_{uuid.uuid4().hex[:12]}"
    existing = next((g for g in page_manager.list_groups() if g.get("id") == group["page_group_id"]), None)
    page_manager.add_or_update_group(group["page_group_id"], group["name"], list(group.get("page_ids") or []),
                                     (existing or {}).get("folder_binding") or str(OUTPUT_DIR),
                                     (existing or {}).get("schedule_config"))


def page_in_token_group(page, group):
    """Use the group's own verified assignment without altering queued posts."""
    page = dict(page)
    tid = (group.get("page_token_bindings") or {}).get(str(page.get("page_id")))
    tid = str(tid or page.get("token_id") or "")
    page["token_id"] = tid if tid in {str(t) for t in group.get("token_ids", [])} else ""
    return page

@app.route("/api/token-groups", methods=["GET"])
def api_list_token_groups():
    vault_entries = token_vault.list_tokens(mask=False)
    vault_counts = {}
    for token in vault_entries:
        token_id = str(token.get("id") or "")
        vault_counts[token_id] = vault_counts.get(token_id, 0) + 1
    vault_ids = {token_id for token_id, count in vault_counts.items() if count == 1}
    pages = page_manager.list_pages()
    posts = load_posts()
    groups = []
    for raw in load_token_groups():
        group = dict(raw)
        token_ids = {str(tid) for tid in group.get("token_ids", [])}
        page_ids = {str(pid) for pid in group.get("page_ids", [])}
        group_pages = [page for page in pages if str(page.get("page_id") or "") in page_ids]
        bound_pages = [page for page in group_pages if token_ids.intersection((page.get("token_bindings") or {}).keys())]
        stale_binding = any(
            str(page_in_token_group(page, group).get("token_id") or "") not in vault_ids
            or not token_ids.intersection((page.get("token_bindings") or {}).keys())
            for page in group_pages
        )
        group["health"] = {
            "pages_bound": len({str(page.get("page_id")) for page in bound_pages}),
            "vault_present": len(token_ids & vault_ids),
            "vault_total": len(token_ids),
            "duplicate_ids": sorted(token_id for token_id in token_ids if vault_counts.get(token_id, 0) > 1),
            "scheduled_posts": sum(1 for post in posts if post.get("status") == "scheduled" and str(post.get("token_id") or "") in token_ids),
            "processing_posts": sum(1 for post in posts if post.get("status") in ("processing", "publishing") and str(post.get("token_id") or "") in token_ids),
            "rebind_required": bool(token_ids - vault_ids) or stale_binding or (bool(page_ids) and not group_pages),
        }
        groups.append(group)
    return jsonify({"success": True, "groups": groups})

def _pages_for_source_token(page_source_token_id):
    """Return the cached Page ids owned by one vault token, in stable order."""
    if not page_source_token_id:
        return []
    return sorted({
        str(page.get("page_id")) for page in page_manager.list_pages()
        if (str(page.get("token_id") or "") == page_source_token_id
            or page_source_token_id in (page.get("token_bindings") or {})) and page.get("page_id")
    })


def _sync_group_credentials(token_ids):
    """Discover each group credential; never infer access from another token."""
    errors = []
    for token_id in token_ids:
        try:
            entry, discovered = token_vault.refresh_token_pages(token_id)
            if not entry or entry.get("status") != "ACTIVE":
                errors.append({"token_id": token_id, "error": (entry or {}).get("error_msg") or "Token inactive"})
                continue
            page_manager.sync_pages_from_token(entry, discovered)
        except Exception as exc:
            errors.append({"token_id": token_id, "error": str(exc)})
    return errors


def _group_page_ids(token_ids, source_id=""):
    if source_id:
        return _pages_for_source_token(source_id)
    ids = set(_pages_for_source_token(source_id))
    for page in page_manager.list_pages():
        if set(page.get("token_bindings") or {}).intersection(token_ids):
            ids.add(str(page.get("page_id")))
    return sorted(ids - {""})


@app.route("/api/token-groups", methods=["POST"])
def api_save_token_group():
    data = request.json or {}
    # UUID ids prevent two fast saves from replacing the previous group.
    gid = data.get("id") or f"tgrp_{uuid.uuid4().hex[:12]}"
    name = data.get("name", "").strip()
    token_ids = list(dict.fromkeys(str(tid) for tid in data.get("token_ids", []) if tid))
    strategy = data.get("strategy", "least_recently_used")
    note = data.get("note", "").strip()
    has_source = "page_source_token_id" in data
    page_source_token_id = str(data.get("page_source_token_id") or "").strip()

    if not name:
        return jsonify({"error": "Tên nhóm token không được rỗng"}), 400
    vault_ids = {str(item.get("id")) for item in token_vault.list_tokens(mask=False)}
    unknown_ids = sorted(set(token_ids) - vault_ids)
    if unknown_ids:
        return jsonify({"error": "Token không tồn tại trong Vault: " + ", ".join(unknown_ids)}), 404
    if page_source_token_id and page_source_token_id not in vault_ids:
        return jsonify({"error": "Token nguồn Page không tồn tại trong Vault"}), 404
    if page_source_token_id and page_source_token_id not in token_ids:
        return jsonify({"success": False, "error": "Token nguồn phải thuộc nhóm được chọn."}), 400
    sync_errors = _sync_group_credentials(token_ids) if data.get("sync_pages") is True else []
    if sync_errors:
        return jsonify({"success": False, "code": "page_sync_failed", "sync_errors": sync_errors,
                        "error": "Một số Token chưa Sync Page thành công; nhóm chưa được lưu."}), 409
    page_ids = _group_page_ids(token_ids, page_source_token_id)

    with _token_group_lock:
        groups = load_token_groups()
        existing = next((g for g in groups if g.get("id") == gid), None)
        duplicate = next((g for g in groups if g.get("name", "").strip().casefold() == name.casefold() and g.get("id") != gid), None)
        if duplicate:
            return jsonify({"success": False, "error": "Tên nhóm đã tồn tại", "group": duplicate}), 409
        if existing:
            existing["name"] = name
            existing["token_ids"] = token_ids
            existing["strategy"] = strategy
            existing["note"] = note
            if has_source or not existing.get("page_source_token_id"):
                existing["page_source_token_id"] = page_source_token_id
            existing["page_ids"] = _group_page_ids(token_ids, existing.get("page_source_token_id") or "")
            existing["page_token_bindings"] = {pid: tid for pid, tid in (existing.get("page_token_bindings") or {}).items()
                                               if pid in existing["page_ids"] and tid in token_ids}
            existing["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            groups.append({"id": gid, "name": name, "strategy": strategy,
                           "token_ids": token_ids, "note": note,
                           "page_source_token_id": page_source_token_id,
                           "page_ids": page_ids,
                           "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        saved = next(g for g in groups if g.get("id") == gid)
        if data.get("create_page_group") is True or saved.get("page_group_id"):
            sync_linked_page_group(saved)
        save_token_groups(groups)
    saved = next((g for g in groups if g.get("id") == gid), None) or {}
    return jsonify({
        "success": True,
        "message": f"Đã lưu Nhóm Token '{name}' thành công!",
        "group": saved,
        "sync_errors": sync_errors,
    })


@app.route("/api/token-groups/<gid>/rebind-pages", methods=["POST"])
def api_rebind_token_group_pages(gid):
    """Re-snapshot a group's Page ids from its bound source token without any Graph call."""
    groups = load_token_groups()
    group = next((g for g in groups if str(g.get("id")) == str(gid)), None)
    if group is None:
        return jsonify({"success": False, "error": "Nhóm token không tồn tại"}), 404
    source_id = str(group.get("page_source_token_id") or "").strip()
    if not source_id:
        return jsonify({"success": False, "error": "Nhóm này chưa binding Page set"}), 400
    if token_vault.get_token_by_id(source_id) is None:
        return jsonify({"success": False, "error": "Token nguồn không còn tồn tại trong Vault"}), 404
    missing_ids = [str(tid) for tid in group.get("token_ids", []) if token_vault.get_token_by_id(str(tid)) is None]
    if missing_ids:
        return jsonify({"success": False, "code": "token_group_unsynced", "missing_token_ids": missing_ids,
                        "error": "Nhóm còn token thiếu trong Vault; khôi phục token rồi Sync Page trước."}), 409
    page_ids = _group_page_ids([str(tid) for tid in group.get("token_ids", [])], source_id)
    if not page_ids:
        return jsonify({
            "success": False,
            "error": "Token nguồn chưa có Page nào trong cache; hãy Sync Page cho token đó trước",
        }), 409
    group["page_ids"] = page_ids
    group["pages_synced_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if group.get("page_group_id"):
        sync_linked_page_group(group)
    save_token_groups(groups)
    return jsonify({"success": True, "page_ids": page_ids, "group": group})


@app.route("/api/token-groups/<gid>/sync-pages", methods=["POST"])
def api_sync_token_group_pages(gid):
    groups = load_token_groups()
    group = next((g for g in groups if str(g.get("id")) == str(gid)), None)
    if group is None:
        return jsonify({"success": False, "error": "Token group not found."}), 404
    token_ids = [str(tid) for tid in group.get("token_ids", [])]
    missing_ids = [tid for tid in token_ids if token_vault.get_token_by_id(tid) is None]
    if missing_ids:
        return jsonify({"success": False, "code": "token_group_unsynced", "missing_token_ids": missing_ids,
                        "error": "Restore the missing exact Token Vault entries before syncing this group."}), 409
    errors = _sync_group_credentials(token_ids)
    if errors:
        return jsonify({"success": False, "code": "page_sync_failed", "sync_errors": errors,
                        "error": "Some group tokens could not sync Pages; the Page set was not rebound."}), 409
    with _token_group_lock:
        groups = load_token_groups()
        current = next(g for g in groups if str(g.get("id")) == str(gid))
        current["page_ids"] = _group_page_ids(token_ids, str(current.get("page_source_token_id") or ""))
        current["pages_synced_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if current.get("page_group_id"):
            sync_linked_page_group(current)
        save_token_groups(groups)
    return jsonify({"success": True, "synced_token_count": len(token_ids), "page_ids": current["page_ids"], "group": current})

@app.route("/api/token-groups/<gid>", methods=["DELETE"])
def api_delete_token_group(gid):
    groups = load_token_groups()
    before = len(groups)
    new_groups = [g for g in groups if g.get("id") != gid]
    if len(new_groups) == before:
        return jsonify({"success": False, "error": "Nhóm token không tồn tại"}), 404
    save_token_groups(new_groups)
    return jsonify({"success": True, "deleted_id": str(gid), "message": "Đã xóa nhóm token!"})


@app.route("/api/tokens", methods=["GET"])
def api_list_tokens():
    tokens = token_vault.list_tokens(mask=True)
    # Vault counters lag page synchronization; show currently assigned pages.
    page_counts = {}
    for page in page_manager.list_pages():
        token_id = str(page.get("token_id") or "")
        if token_id:
            page_counts[token_id] = page_counts.get(token_id, 0) + 1
    for token in tokens:
        token["pages_count"] = page_counts.get(str(token.get("id")), 0)
        token["operator_label"] = token.get("name") or ""
        token["identity_verified"] = bool(token.get("owner_name"))
        # Bulk-imported tokens can all carry the same operator label (e.g. Bm1).
        # Show the verified Meta owner so each credential remains identifiable.
        token["display_name"] = token.get("owner_name") or token.get("name") or token.get("id")
        token["name"] = token["display_name"]
    return jsonify({"success": True, "tokens": tokens})

@app.route("/api/tokens/health-sync", methods=["POST"])
def api_token_health_sync():
    """Probe every stored credential and move Pages off blocked credentials."""
    from concurrent.futures import ThreadPoolExecutor
    tokens = token_vault.list_tokens(mask=False)
    healthy, blocked = set(), set()
    def check_token(token):
        try:
            response = requests.get("https://graph.facebook.com/v22.0/me",
                                    params={"access_token": token.get("token"), "fields": "id,name"}, timeout=8)
            payload = response.json()
            error = payload.get("error") if isinstance(payload, dict) else None
            if response.ok and not error:
                return token, True, ""
            else:
                return token, False, f"Meta [{(error or {}).get('code', response.status_code)}] {(error or {}).get('message', 'Credential rejected')}"
        except Exception as exc:
            return token, False, sanitize_error(exc)
    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(check_token, tokens))
    for token, ok, error in outcomes:
        (healthy if ok else blocked).add(str(token.get("id")))
        token.update({"status": "ACTIVE" if ok else "ERROR", "error_msg": error,
                      "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    token_vault._save(tokens)
    # Health checks update credential status only. Page ownership is an explicit
    # operator choice and must never change as a side effect of scheduling.
    pages = page_manager.list_pages()
    stale_assignments = sum(str(page.get("token_id") or "") not in healthy for page in pages)
    global _last_meta_health_sync
    _last_meta_health_sync = time.monotonic()
    return jsonify({"success": True, "healthy_tokens": len(healthy),
                    "blocked_tokens": len(blocked), "stale_assignments": stale_assignments,
                    "reassigned_pages": 0, "blocked_token_ids": sorted(blocked)})

_last_meta_health_sync = 0.0

def _ensure_recent_meta_health():
    """Fail before queue creation if Meta no longer accepts Page credentials."""
    if app.testing or time.monotonic() - _last_meta_health_sync < 120:
        return None
    result = api_token_health_sync()
    response = result[0] if isinstance(result, tuple) else result
    return result if response.status_code != 200 else None

@app.route("/api/tokens", methods=["POST"])
def api_add_token():
    data = request.json or {}
    raw_tokens_input = data.get("tokens_input") or data.get("token") or ""
    raw_tokens_input = str(raw_tokens_input).strip()
    default_name = data.get("name", "").strip()
    kind = data.get("kind", "SYS")
    note = data.get("note", "").strip()
    page_sync_mode = str(data.get("page_sync_mode") or "each").strip().lower()
    import_group_id = str(data.get("token_group_id") or "").strip()
    import_group_name = str(data.get("token_group_name") or "").strip()
    if import_group_id and not any(g.get("id") == import_group_id for g in load_token_groups()):
        return jsonify({"success": False, "error": "Nhóm Token được chọn không còn tồn tại."}), 404
    if page_sync_mode not in {"representative", "each", "none"}:
        return jsonify({"error": "page_sync_mode không hợp lệ"}), 400
    
    if not raw_tokens_input:
        return jsonify({"error": "Thiếu mã token"}), 400
    
    # Check if multiple lines or single
    lines = [l.strip() for l in raw_tokens_input.splitlines() if l.strip()]
    if not lines:
        return jsonify({"error": "Nội dung token không hợp lệ"}), 400

    # Parse every line up front so a deferred representative retry can reuse its slot.
    entries = []
    for idx, line in enumerate(lines):
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
        entries.append({"name": item_name, "token": item_token})

    results = []
    synced_page_ids = set()
    representative_idx = None

    # Store and validate every token with lightweight /me first. Representative
    # mode then walks only the ACTIVE candidates through /me/accounts in order.
    for item in entries:
        try:
            entry, pages = token_vault.add_token(
                item["name"], item["token"], kind, note,
                discover_pages=(page_sync_mode == "each"),
            )
            if page_sync_mode == "each" and entry.get("status") == "ACTIVE":
                page_manager.sync_pages_from_token(entry, pages)
                for page in pages:
                    page_id = page.get("id") or page.get("page_id")
                    if page_id:
                        synced_page_ids.add(str(page_id))
            results.append({
                "id": entry.get("id"),
                "name": entry.get("name"),
                "status": entry.get("status"),
                "error_msg": entry.get("error_msg", ""),
                "pages_count": len(pages),
                "page_sync": "synced" if page_sync_mode == "each" and entry.get("status") == "ACTIVE" else "skipped",
                "is_representative": False,
            })
        except Exception as ex:
            results.append({
                "name": item["name"],
                "status": "ERROR",
                "error_msg": str(ex),
                "pages_count": 0,
                "page_sync": "failed",
                "is_representative": False,
            })

    if page_sync_mode == "representative":
        for idx, item in enumerate(entries):
            if results[idx].get("status") != "ACTIVE":
                continue
            try:
                page_sync = token_vault.discover_pages(
                    item["token"], owner_name=str(results[idx].get("name") or "")
                )
            except Exception as ex:
                page_sync = {"status": "ERROR", "error": str(ex), "pages": []}
            if page_sync.get("status") != "ACTIVE":
                results[idx]["page_sync"] = "failed"
                results[idx]["page_sync_error"] = page_sync.get("error", "")
                continue
            pages = page_sync.get("pages", [])
            entry = token_vault.get_token_by_id(results[idx]["id"]) or {}
            token_vault.record_page_sync(results[idx]["id"], pages)
            page_manager.sync_pages_from_token(entry, pages)
            for page in pages:
                page_id = page.get("id") or page.get("page_id")
                if page_id:
                    synced_page_ids.add(str(page_id))
            representative_idx = idx
            results[idx]["pages_count"] = len(pages)
            results[idx]["page_sync"] = "synced"
            results[idx]["is_representative"] = True
            break

    representative_label = ""
    representative = results[representative_idx] if representative_idx is not None else None
    if representative is not None:
        representative_label = f"#{representative_idx + 1} {representative.get('name')}"

    import_group = None
    imported_ids = [item["id"] for item in results if item.get("id")]
    if imported_ids and (import_group_id or import_group_name):
        with _token_group_lock:
            groups = load_token_groups()
            import_group = next((g for g in groups if (import_group_id and g.get("id") == import_group_id)
                                 or (not import_group_id and g.get("name", "").casefold() == import_group_name.casefold())), None)
            if import_group is None:
                import_group = {"id": f"tgrp_{uuid.uuid4().hex[:12]}", "name": import_group_name,
                                "token_ids": [], "strategy": "least_recently_used", "page_source_token_id": "",
                                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                groups.append(import_group)
            import_group["token_ids"] = list(dict.fromkeys(list(import_group.get("token_ids") or []) + imported_ids))
            if representative and not import_group.get("page_source_token_id"):
                import_group["page_source_token_id"] = representative["id"]
            import_group["page_ids"] = _group_page_ids(import_group["token_ids"], str(import_group.get("page_source_token_id") or ""))
            sync_linked_page_group(import_group)
            save_token_groups(groups)

    return jsonify({
        "success": True,
        "count": len(results),
        "results": results,
        "synced_pages": len(synced_page_ids),
        "page_sync_mode": page_sync_mode,
        "representative": ({"id": representative.get("id"), "name": representative.get("name"),
                            "label": representative_label} if representative else None),
        "token": results[0] if results else None,
        "token_group": import_group,
    })

@app.route("/api/tokens/<token_id>/refresh-pages", methods=["POST"])
def api_refresh_token_pages(token_id):
    entry, pages = token_vault.refresh_token_pages(token_id)
    if entry is None:
        return jsonify({"success": False, "error": "Token không tồn tại trong Vault"}), 404
    if entry.get("status") != "ACTIVE":
        return jsonify({"success": False, "error": entry.get("error_msg") or "Token không hợp lệ"}), 400
    page_manager.sync_pages_from_token(entry, pages)
    return jsonify({
        "success": True,
        "token_id": token_id,
        "synced_pages": len({str(page.get("page_id")) for page in pages if page.get("page_id")}),
    })

@app.route("/api/tokens/<token_id>", methods=["DELETE"])
def api_delete_token(token_id):
    data = request.get_json(silent=True) or {}
    return _delete_token_set([token_id], migration_token_id=str(data.get("migration_token_id") or ""))

@app.route("/api/tokens/bulk-delete", methods=["POST"])
def api_bulk_delete_tokens():
    ids = (request.json or {}).get("token_ids")
    if not isinstance(ids, list) or not ids or len(ids) != len(set(map(str, ids))):
        return jsonify({"success": False, "error": "Chọn token hợp lệ để xóa"}), 400
    data = request.get_json(silent=True) or {}
    return _delete_token_set([str(item) for item in ids], migration_token_id=str(data.get("migration_token_id") or ""))

def _delete_token_set(token_ids, migration_token_id=""):
    ids = set(token_ids)
    vault_ids = {str(t.get("id")) for t in token_vault.list_tokens(mask=False)}
    if ids - vault_ids:
        return jsonify({"success": False, "error": "Một số token không còn trong kho"}), 404
    pages = page_manager.list_pages()
    assigned_pages = [p for p in pages if str(p.get("token_id") or "") in ids]
    referenced_pages = [p for p in pages if str(p.get("token_id") or "") in ids
                        or ids.intersection({str(tid) for tid, binding in (p.get("token_bindings") or {}).items() if binding})]
    posts = load_posts()
    referenced_posts = [p for p in posts if str(p.get("token_id") or "") in ids and (
        p.get("status") in ("scheduled", "meta_handoff", "publishing", "processing", "meta_scheduled")
        or (p.get("status") == "failed" and p.get("retryable") and p.get("retry_stage") == "meta_preflight")
    )]
    pending_comment_file = BASE_DIR / "data" / "pending_first_comments.json"
    try:
        pending_comments = json.loads(pending_comment_file.read_text(encoding="utf-8")) if pending_comment_file.exists() else []
        if not isinstance(pending_comments, list):
            raise ValueError
    except (OSError, ValueError, json.JSONDecodeError):
        return jsonify({"success": False, "code": "pending_comment_queue_unreadable",
                        "error": "Cannot verify pending First Comment credentials; token deletion is paused."}), 409
    referenced_comments = [item for item in pending_comments if item.get("status") in ("pending", "verification_pending")
                           and str(item.get("token_id") or "") in ids]
    migration_token_id = str(migration_token_id or "").strip()
    if migration_token_id:
        if migration_token_id in ids:
            return jsonify({"success": False, "code": "invalid_migration_target", "error": "Migration target must be a different token."}), 400
        target = token_vault.get_token_by_id(migration_token_id)
        if not target or target.get("status") != "ACTIVE":
            return jsonify({"success": False, "code": "invalid_migration_target", "error": "Migration target must exist and be active."}), 409
        unsafe_posts = [p for p in referenced_posts if p.get("status") in ("meta_handoff", "publishing", "processing", "meta_scheduled")]
        if unsafe_posts:
            return jsonify({"success": False, "code": "token_in_use", "migration_required": True,
                            "error": "Meta outcome or handed-off schedule is unresolved; reconcile it with the original credential before deleting.",
                            "post_ids": [str(p.get("id") or "") for p in unsafe_posts]}), 409
        for page in referenced_pages:
            verdict = resolve_page_token({**page, "token_id": migration_token_id}, token_vault, page_manager)
            if not verdict.get("ok"):
                return jsonify({"success": False, "code": "migration_target_unverified", "page_id": str(page.get("page_id") or ""),
                                "error": verdict.get("action") or "Target token has no verified mapping for this Page."}), 409
        page_by_id = {str(page.get("page_id") or ""): page for page in pages}
        for post in referenced_posts:
            page = page_by_id.get(str(post.get("page_id") or ""))
            if not page:
                return jsonify({"success": False, "code": "migration_target_unverified", "post_id": str(post.get("id") or ""),
                                "error": "Could not verify a Page mapping for a queued post."}), 409
            verdict = resolve_page_token({**page, "token_id": migration_token_id}, token_vault, page_manager)
            if not verdict.get("ok"):
                return jsonify({"success": False, "code": "migration_target_unverified", "post_id": str(post.get("id") or ""),
                                "error": verdict.get("action") or "Target token has no verified mapping for this scheduled Page."}), 409
            post["token_id"] = migration_token_id
            post["token"] = verdict["token"]
            post["token_name"] = verdict.get("token_name") or target.get("name") or migration_token_id
            post["token_migrated_from"] = next(iter(ids)) if len(ids) == 1 else "bulk_migration"
            post["token_migrated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        posts_by_id = {str(post.get("id") or ""): post for post in posts}
        for item in referenced_comments:
            post = posts_by_id.get(str(item.get("post_id") or ""))
            page = page_by_id.get(str((post or {}).get("page_id") or "")) if "page_by_id" in locals() else None
            if not page:
                page = next((entry for entry in pages if any(
                    str(binding.get("page_token") or "") == str(item.get("page_token") or "")
                    for binding in (entry.get("token_bindings") or {}).values()
                )), None)
            if not page:
                return jsonify({"success": False, "code": "migration_target_unverified",
                                "post_id": str(item.get("post_id") or ""),
                                "error": "Could not verify the Page for a pending First Comment."}), 409
            verdict = resolve_page_token({**page, "token_id": migration_token_id}, token_vault, page_manager)
            if not verdict.get("ok"):
                return jsonify({"success": False, "code": "migration_target_unverified",
                                "post_id": str(item.get("post_id") or ""),
                                "error": verdict.get("action") or "Target token has no verified mapping for this comment's Page."}), 409
            item["token_id"] = migration_token_id
            item["page_token"] = verdict["token"]
        for page in assigned_pages:
            verdict = resolve_page_token({**page, "token_id": migration_token_id}, token_vault, page_manager)
            page["token_id"] = migration_token_id
            page["token_name"] = target.get("name") or migration_token_id
            page["page_token"] = verdict["token"]
            page["mapping_status"] = "VERIFIED"
            page["mapping_verified_at"] = verdict.get("verified_at", "")
    elif referenced_pages or referenced_posts or referenced_comments:
        affected_pages = sorted({str(p.get("page_id") or "") for p in referenced_pages} - {""})
        affected_posts = [str(p.get("id") or "") for p in referenced_posts]
        return jsonify({"success": False, "code": "token_in_use", "migration_required": True,
                        "error": "Token is referenced by Page bindings or queued posts. Choose a verified migration target; processing Meta outcomes cannot be migrated.",
                        "assigned_pages": len(affected_pages), "queued_posts": len(affected_posts),
                        "pending_first_comments": len(referenced_comments),
                        "page_ids": affected_pages, "post_ids": affected_posts}), 409
    if migration_token_id:
        # Persist verified replacements before removing the old credential.
        page_manager.save_pages(pages)
        save_posts(posts)
        if referenced_comments:
            pending_comment_file.parent.mkdir(parents=True, exist_ok=True)
            pending_comment_file.write_text(json.dumps(pending_comments, indent=2, ensure_ascii=False), encoding="utf-8")
    with _token_group_lock:
        groups = load_token_groups()
        for group in groups:
            if migration_token_id and ids.intersection({str(tid) for tid in group.get("token_ids", [])}):
                group["token_ids"] = list(dict.fromkeys([str(tid) for tid in group.get("token_ids", []) if str(tid) not in ids] + [migration_token_id]))
            else:
                group["token_ids"] = [tid for tid in group.get("token_ids", []) if tid not in ids]
            if group.get("page_source_token_id") in ids:
                group["page_source_token_id"] = migration_token_id
        save_token_groups(groups)
        for page in pages:
            bindings = page.get("token_bindings")
            if isinstance(bindings, dict):
                for tid in ids:
                    bindings.pop(tid, None)
        page_manager.save_pages(pages)
        removed = token_vault.delete_tokens(ids)
    return jsonify({"success": True, "deleted_count": len(removed)})

@app.route("/api/pages", methods=["GET"])
def api_list_pages():
    pages = page_manager.list_pages()
    groups = page_manager.list_groups()
    valid_groups = {str(g.get("id")): g for g in groups if g.get("id")}
    token_names = {str(t.get("id")): (t.get("owner_name") or t.get("name") or t.get("id"))
                   for t in token_vault.list_tokens(mask=True)}
    token_groups = load_token_groups()
    # Page mapping stores the last successful publish counter, while the post
    # queue is the authoritative source for work scheduled during the current
    # run. Expose both so the UI never shows a misleading zero during a batch.
    try:
        posts = load_posts()
    except Exception:
        posts = []
    stats = {}
    for post in posts if isinstance(posts, list) else []:
        pid = str(post.get("page_id") or "").strip()
        if not pid:
            continue
        row = stats.setdefault(pid, {"published_count": 0, "scheduled_count": 0, "publishing_count": 0})
        status = str(post.get("status") or "").lower()
        if status in ("published", "success"):
            row["published_count"] += 1
        elif status == "publishing":
            row["publishing_count"] += 1
        elif status in ("scheduled", "processing"):
            row["scheduled_count"] += 1
    enriched = []
    for page in pages:
        item = dict(page)
        pid = str(item.get("page_id") or "").strip()
        assigned_id = str(item.get("token_id") or "")
        item["token_assignment_valid"] = assigned_id in token_names
        item["token_name"] = token_names.get(assigned_id, "Chưa gán token hiện tại")
        item["token_group_ids"] = [str(group.get("id")) for group in token_groups
                                   if pid in {str(value) for value in group.get("page_ids", [])}]
        item["token_group_names"] = [group.get("name") for group in token_groups if str(group.get("id")) in item["token_group_ids"]]
        item["group_token_assignments"] = {str(group["id"]): page_in_token_group(page, group).get("token_id")
                                           for group in token_groups if str(group.get("id")) in item["token_group_ids"]}
        item.update(stats.get(pid, {"published_count": 0, "scheduled_count": 0, "publishing_count": 0}))
        # Never display a deleted/stale group label as if it still existed.
        group_ids = [str(gid) for gid in (item.get("group_ids") or []) if str(gid) in valid_groups]
        for group in groups:
            gid = str(group.get("id") or "")
            if gid and gid not in group_ids and pid in {str(p) for p in (group.get("page_ids") or [])}:
                group_ids.append(gid)
        item["group_ids"] = group_ids
        item["group_name"] = valid_groups[group_ids[0]].get("name") if group_ids else "Chưa nhóm"
        enriched.append(item)
    return jsonify({
        "success": True,
        "pages": enriched,
        "groups": groups,
        "mapping_health": page_manager.mapping_health(),
    })

@app.route("/api/pages/mapping-health", methods=["GET"])
def api_page_mapping_health():
    return jsonify({"success": True, "data": page_manager.mapping_health()})

@app.route("/api/groups", methods=["GET"])
def api_list_groups():
    groups = page_manager.list_groups()
    linked = {str(g.get("page_group_id")): str(g["id"]) for g in load_token_groups() if g.get("page_group_id")}
    groups = [{**g, "token_group_id": linked.get(str(g.get("id")), "")} for g in groups]
    return jsonify({"success": True, "groups": groups})


@app.route("/api/folders", methods=["GET"])
def api_folder_browser():
    """Browse local directories for the operator's Folder Binding selection."""
    import string
    try:
        folder = Path(str(request.args.get("path") or OUTPUT_DIR).strip().strip('"')).expanduser().resolve()
        if not folder.is_dir():
            return jsonify({"success": False, "error": "Thư mục không tồn tại hoặc không truy cập được."}), 400
        children = []
        for child in folder.iterdir():
            try:
                if child.is_dir():
                    children.append({"name": child.name, "path": str(child)})
            except OSError:
                continue
        children.sort(key=lambda child: child["name"].casefold())
        drives = [f"{letter}:\\" for letter in string.ascii_uppercase if Path(f"{letter}:\\").is_dir()] if os.name == "nt" else ["/"]
        return jsonify({"success": True, "path": str(folder), "parent": str(folder.parent),
                        "default_path": str(OUTPUT_DIR), "directories": children[:500], "drives": drives})
    except (OSError, ValueError):
        return jsonify({"success": False, "error": "Không thể đọc thư mục này; bạn vẫn có thể nhập đường dẫn nguồn."}), 400

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
    from src.content_packages import scheduled_video_path
    from multi_pc.meta_scheduling import MetaScheduleTimeError, parse_meta_schedule_time
    data = request.json or {}
    if data.get("schedule_time"):
        blocked = _ensure_recent_meta_health()
        if blocked is not None:
            return blocked
    page_id = data.get("page_id")
    page_ids = data.get("page_ids") or []
    group_id = data.get("group_id")
    clip_filename = data.get("filename")
    title = data.get("title", "")
    caption = data.get("caption", "")
    first_comment = data.get("first_comment", "")
    article_url = str(data.get("article_url") or data.get("website_url") or "").strip()
    first_comment = str(first_comment or "").strip()
    if article_url and first_comment and article_url not in first_comment:
        first_comment = f"{first_comment}\n{article_url}".strip()
    schedule_time = data.get("schedule_time") # ISO or "YYYY-MM-DD HH:MM" or timestamp
    publish_mode = str(data.get("publish_mode") or "app_queue").strip().lower()
    token_group_id = str(data.get("token_group_id") or "").strip()
    profile_store = load_profile_store(FIRST_COMMENT_PROFILES_FILE)
    first_comment_profile_id = str(data.get("first_comment_profile_id") or profile_store.get("default_profile_id") or "builtin_general")
    if first_comment_profile_id not in {str(profile.get("id")) for profile in profile_store.get("profiles", [])}:
        return jsonify({"success": False, "code": "first_comment_profile_missing", "error": "First Comment profile not found."}), 400
    if publish_mode not in ("app_queue", "meta_scheduled"):
        return jsonify({"success": False, "code": "invalid_publish_mode", "error": "publish_mode must be app_queue or meta_scheduled."}), 400
    if publish_mode == "meta_scheduled" and not schedule_time:
        return jsonify({"success": False, "code": "schedule_time_required", "error": "Meta scheduling requires a future publish time."}), 400
    stagger_minutes = max(1, int(data.get("stagger_minutes", 15)))
    from multi_pc.publishing_settings import load_publishing_settings, save_publishing_settings
    try:
        posting_threads = (save_publishing_settings(POSTS_FILE.parent, data["posting_threads"])
                           if "posting_threads" in data else load_publishing_settings(POSTS_FILE.parent))["posting_threads"]
    except (ValueError, TypeError) as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    
    if not clip_filename:
        return jsonify({"error": "Thiếu tên file clip"}), 400
    
    try:
        video_path = scheduled_video_path(OUTPUT_DIR, clip_filename)
    except (ValueError, FileNotFoundError, OSError) as exc:
        return jsonify({"success": False, "error": str(exc), "code": "invalid_video_path"}), 400

    pages = page_manager.list_pages()
    groups = page_manager.list_groups()

    target_page_ids = []
    if page_id:
        target_page_ids.append(str(page_id).strip())
    if page_ids and isinstance(page_ids, list):
        for pid in page_ids:
            pid = str(pid).strip()
            if pid and pid not in target_page_ids:
                target_page_ids.append(pid)
    if group_id:
        grp = next((g for g in groups if isinstance(g, dict) and str(g.get("id")) == str(group_id)), None)
        if grp:
            for pid in (grp.get("page_ids", []) if isinstance(grp.get("page_ids", []), list) else []):
                pid = str(pid).strip()
                if pid not in target_page_ids:
                    target_page_ids.append(pid)

    if not token_group_id and group_id:
        token_group_id = next((str(g["id"]) for g in load_token_groups()
                               if str(g.get("page_group_id") or "") == str(group_id)), "")
    selected_token_group = None
    if token_group_id:
        selected_token_group = next((g for g in load_token_groups() if str(g.get("id")) == token_group_id), None)
        if selected_token_group is None:
            return jsonify({"success": False, "code": "token_group_missing", "error": "Token group not found."}), 404
        missing_group_tokens = [str(token_id) for token_id in selected_token_group.get("token_ids", [])
                                if token_vault.get_token_by_id(str(token_id)) is None]
        if missing_group_tokens:
            return jsonify({"success": False, "code": "credential_missing", "missing_token_ids": missing_group_tokens,
                            "error": "Nhóm có credential thiếu hoặc ID trùng trong Token Vault; khôi phục và Sync Page trước khi lên lịch."}), 409
        token_page_ids = {str(pid).strip() for pid in selected_token_group.get("page_ids", []) if str(pid).strip()}
        if not token_page_ids:
            return jsonify({"success": False, "code": "token_group_unsynced", "error": "Nhóm này chưa có Page đã đồng bộ; hãy Sync Page trước."}), 409
        requested_pages = {str(page_id).strip()} if page_id else {str(pid).strip() for pid in page_ids if str(pid).strip()}
        outside = requested_pages - token_page_ids
        if outside:
            return jsonify({"success": False, "code": "page_outside_token_group", "page_ids": sorted(outside),
                            "error": "Page đã chọn không thuộc nhóm token này."}), 409
        target_page_ids = [pid for pid in target_page_ids if pid in token_page_ids]
        pages = [page_in_token_group(page, selected_token_group) if str(page.get("page_id")) in token_page_ids else page for page in pages]

    if not target_page_ids:
        return jsonify({"error": "Vui lòng chọn ít nhất 1 Fanpage hoặc 1 Nhóm Page để đăng"}), 400

    if not schedule_time and len(target_page_ids) > 1:
        return jsonify({
            "success": False,
            "code": "multi_page_requires_schedule",
            "error": "Đăng nhiều Page cần đặt lịch để giãn cách request Meta; chọn thời gian bắt đầu rồi thử lại.",
        }), 400

    full_description = f"{title}\n\n{caption}".strip()
    results = []
    success_count = 0
    pages_updated = False

    # Resolve schedule targets up-front so Meta permission preflight can fail closed
    # before any post is queued.
    target_pages = []
    for pid in target_page_ids:
        p_info = next((p for p in pages if isinstance(p, dict) and str(p.get("page_id")) == str(pid)), None)
        if not p_info:
            results.append({"page_id": pid, "success": False, "error": "Không tìm thấy thông tin Page"})
            continue
        target_pages.append(p_info)

    block_website_fields = None
    schedule_target_pages = [] if schedule_time else []
    if schedule_time:
        try:
            s_str = str(schedule_time).strip().replace("T", " ")
            if len(s_str) == 16:
                s_str += ":00"
            dt = datetime.strptime(s_str[:19], "%Y-%m-%d %H:%M:%S")
            parsed_schedule_ts = int(dt.timestamp())
        except Exception:
            try:
                parsed_schedule_ts = int(schedule_time)
            except Exception:
                return jsonify({"success": False, "error": "Thời gian lên lịch không hợp lệ; dùng YYYY-MM-DD HH:MM hoặc timestamp.", "code": "invalid_schedule_time"}), 400
        if parsed_schedule_ts <= int(time.time()) + 5:
            return jsonify({"success": False, "error": "Thời gian lên lịch phải ở tương lai (ít nhất 5 giây). Hãy chọn lại giờ đăng.", "code": "schedule_time_in_past"}), 400
        preflight = preflight_pages(target_pages, token_vault, page_manager)
        if not preflight.get("ok"):
            return jsonify({"success": False, "error": 'Preflight quyền đăng bài thất bại', **preflight["blocked"]}), 400
        for ready in preflight["ready"]:
            page_record = next((p for p in target_pages if str(p.get("page_id")) == ready["page_id"]), None)
            if page_record is None:
                continue
            schedule_target_pages.append((page_record, ready))
        if selected_token_group:
            allowed_tokens = {str(tid) for tid in selected_token_group.get("token_ids", [])}
            outside = [ready["page_id"] for _page, ready in schedule_target_pages if str(ready["token_id"]) not in allowed_tokens]
            if outside:
                return jsonify({"success": False, "code": "page_token_outside_group", "page_ids": outside,
                                "error": "Page không có mapping đã xác minh thuộc nhóm token đã chọn."}), 409
        if publish_mode == "meta_scheduled":
            try:
                parsed_schedule_ts = parse_meta_schedule_time(parsed_schedule_ts)
            except MetaScheduleTimeError as exc:
                return jsonify({"success": False, "code": exc.code, "error": str(exc)}), 400
            # Validate every staggered Page before the first upload begins.
            offsets = paced_offsets_by_token(
                [ready["token_id"] for _page, ready in schedule_target_pages],
                global_seconds=0, token_seconds=stagger_minutes * 60,
            )
            try:
                for offset in offsets:
                    parse_meta_schedule_time(parsed_schedule_ts + offset)
            except MetaScheduleTimeError as exc:
                return jsonify({"success": False, "code": exc.code, "error": str(exc)}), 400

    # A direct publish must never report success without a Website-linked
    # First Comment. Scheduled posts may wait for their content package.
    parsed_article = urlparse(article_url)
    article_url_valid = parsed_article.scheme in ("http", "https") and bool(parsed_article.netloc)
    if article_url and not article_url_valid:
        return jsonify({"success": False, "error": "Link bài Website không hợp lệ.", "code": "invalid_article_url"}), 400
    if not schedule_time and not article_url_valid:
        return jsonify({
            "success": False,
            "error": "Bắt buộc nhập link bài Website trước khi đăng Reel; ứng dụng sẽ gắn link vào First Comment.",
            "code": "website_article_required",
        }), 400
    if schedule_time and not article_url_valid and not bool(data.get("auto_first_comment", False)):
        return jsonify({
            "success": False,
            "error": "Lịch đăng cần link bài Website hoặc bật tự động tạo bài và First Comment.",
            "code": "website_article_required",
        }), 400
    if publish_mode == "meta_scheduled":
        if article_url_valid and not first_comment:
            try:
                from src.first_comment_profiles import profile_first_comment
                generated = generate_curiosity_comment_with_llm(
                    title, article_url, enable_llm=bool(data.get("use_llm_comment", True)),
                    profile_id=first_comment_profile_id,
                )
                first_comment = str(generated or "").strip()
                fallback_value = profile_first_comment(title, article_url, first_comment_profile_id, profile_store)
                data["first_comment_source"] = "template_fallback" if first_comment == fallback_value else "llm"
            except Exception as exc:
                return jsonify({"success": False, "code": "first_comment_generation_failed", "error": sanitize_error(exc)}), 502
        if not article_url_valid or not first_comment or article_url not in first_comment:
            return jsonify({"success": False, "code": "meta_schedule_comment_required",
                            "error": "Meta scheduling needs a verified Website URL and a ready First Comment that contains that URL."}), 400
        if first_comment.count(article_url) != 1:
            return jsonify({"success": False, "code": "first_comment_url_count", "error": "First Comment must contain the exact Website URL once."}), 400

    # The website article is generated asynchronously from the content queue; the
    # schedule call must not block on CMS or LLM latency.
    scheduled_posts = load_posts() if schedule_time else []
    scheduled_package_ids = set()
    website_fields = block_website_fields

    # Tinh toan thoi gian hen gio co stagger cho tung page
    base_schedule_ts = None
    if schedule_time:
        base_schedule_ts = parsed_schedule_ts

    # Seed every scheduled target with its exact, verified token so the background
    # publisher never resolves a stale/fallback credential later.
    for _page_record, ready in schedule_target_pages:
        _page_record["page_token"] = ready["token"]
        _page_record["token_id"] = ready["token_id"]

    scheduled_offsets = paced_offsets_by_token(
        [next((ready["token_id"] for record, ready in schedule_target_pages
               if str(record.get("page_id")) == pid), pid) for pid in target_page_ids],
        global_seconds=0,
        token_seconds=stagger_minutes * 60,
    ) if schedule_time else []

    for idx, pid in enumerate(target_page_ids):
        p_info = next((p for p in pages if isinstance(p, dict) and str(p.get("page_id")) == str(pid)), None)
        if not p_info:
            continue

        p_token = p_info.get("page_token")
        # Keep the verified binding explicit for both scheduled and immediate
        # publishes. Immediate publishes do not enter the schedule preflight
        # branch, but the persistence path still needs a safe token_id value.
        verified = None

        # Tinh gio hen kem jitter/stagger cho page nay neu co schedule
        curr_sched = None
        if base_schedule_ts:
            curr_sched = base_schedule_ts + scheduled_offsets[idx]

        if curr_sched:
            verified = next((ready for record, ready in schedule_target_pages if record is p_info), None)
            if verified is None:
                # Preflight already reported the blocking target; never schedule
                # a Page whose credential was not verified for this exact page_id.
                results.append({
                    "page_id": pid,
                    "page_name": p_info.get("page_name"),
                    "success": False,
                    "error": "Page chưa được xác minh quyền đăng bài cho lịch này",
                    "reconnect_required": True,
                })
                continue
            p_token = verified["token"]
            duplicate = next((post for post in scheduled_posts if
                post.get("page_id") == pid and
                (post.get("media_file") or post.get("clip_filename")) == clip_filename and
                post.get("status") in ("scheduled", "meta_scheduled", "publishing", "processing", "published")
            ), None)
            if duplicate:
                results.append({
                    "page_id": pid,
                    "page_name": p_info.get("page_name"),
                    "success": False,
                    "error": "Video này đã có trong hàng đợi hoặc đã đăng cho Page",
                    "duplicate_post_id": duplicate.get("id"),
                })
                continue
            scheduled_dt = datetime.fromtimestamp(curr_sched).strftime("%Y-%m-%d %H:%M:%S")
            post_id = f"post_{int(time.time())}_{uuid.uuid4().hex[:6]}"
            if publish_mode == "meta_scheduled":
                # Persist the exact token binding and an ambiguous-outcome guard
                # before sending the irreversible upload/finish requests.
                post_entry = {
                    "id": post_id, "title": title, "content": caption,
                    "page_id": pid, "page_name": p_info.get("page_name", pid), "type": "reel",
                    "media_file": clip_filename, "first_comment": first_comment,
                    "first_comment_snapshot": first_comment,
                    "first_comment_profile_id": first_comment_profile_id,
                    "first_comment_source": str(data.get("first_comment_source") or "manual"),
                    "first_comment_status": "ready", "article_url": article_url,
                    "website_status": "ready", "auto_first_comment": False,
                    "status": "processing", "publish_mode": "meta_scheduled", "scheduled_time": scheduled_dt,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "token_id": verified["token_id"], "token_group_id": token_group_id,
                    "meta_scheduled_publish_time": curr_sched,
                    "meta_schedule_status": "upload_started", "meta_schedule_verified_at": "",
                    "meta_reconcile_attempts": 0, "meta_next_check_at": time.time() + 60,
                    "retryable": False, "retry_stage": "meta_schedule_verification",
                    "error": "Meta schedule upload started; do not retry until read-only reconciliation completes.",
                }
                scheduled_posts.insert(0, post_entry)
                save_posts(scheduled_posts)
                def persist_upload_id(meta_video_id):
                    post_entry.update({"meta_upload_video_id": meta_video_id, "meta_video_id": meta_video_id,
                                       "meta_schedule_status": "upload_initialized"})
                    save_posts(scheduled_posts)
                res = reel_poster.publish_reel(
                    page_id=pid, page_token=p_token, video_path=str(video_path),
                    description=full_description, first_comment=first_comment,
                    schedule_time=curr_sched, token_id=verified["token_id"],
                    post_id=post_id,
                    on_upload_initialized=persist_upload_id,
                )
                if res.get("success") and res.get("status") == "SCHEDULED" and res.get("meta_video_id"):
                    post_entry.update({
                        "status": "meta_scheduled", "meta_video_id": str(res["meta_video_id"]),
                        "meta_post_id": str(res.get("meta_post_id") or ""),
                        "meta_upload_video_id": str(res.get("meta_video_id") or ""),
                        "meta_scheduled_publish_time": int(res.get("scheduled_publish_time") or curr_sched),
                        "meta_schedule_status": "scheduled",
                        "outcome_unknown": False,
                        "meta_schedule_verified_at": res.get("meta_schedule_verified_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "first_comment_status": "pending" if (res.get("comment_result") or {}).get("success") else "queue_failed",
                        "first_comment_queue_id": (res.get("comment_result") or {}).get("queue_id") or "",
                        "error": "", "retryable": False,
                    })
                    success_count += 1
                    results.append({"page_id": pid, "page_name": p_info.get("page_name"), "success": True,
                                    "status": "META_SCHEDULED", "post_id": post_id,
                                    "meta_video_id": post_entry["meta_video_id"],
                                    "scheduled_publish_time": post_entry["meta_scheduled_publish_time"],
                                    "meta_schedule_status": "scheduled",
                                    "first_comment_status": post_entry["first_comment_status"]})
                elif res.get("outcome_unknown"):
                    post_entry.update({
                        "status": "processing", "outcome_unknown": True, "retryable": False,
                        "meta_post_id": str(res.get("meta_post_id") or ""),
                        "meta_upload_video_id": str(res.get("upload_video_id") or post_entry.get("meta_upload_video_id") or ""),
                        "meta_video_id": str(res.get("meta_video_id") or res.get("upload_video_id") or post_entry.get("meta_video_id") or ""),
                        "meta_schedule_status": str(res.get("meta_schedule_status") or "verification_pending"),
                        "error": str(res.get("error") or "Meta outcome unknown; reconcile before retry."),
                    })
                    results.append({"page_id": pid, "page_name": p_info.get("page_name"), "success": False,
                                    "processing": True, "outcome_unknown": True, "post_id": post_id,
                                    "meta_schedule_status": post_entry["meta_schedule_status"],
                                    "error": "Meta outcome is being reconciled; do not retry."})
                else:
                    post_entry.update({"status": "failed", "meta_schedule_status": "rejected",
                                       "retryable": not bool(res.get("outcome_unknown")),
                                       "retry_stage": "meta_schedule_rejected",
                                       "outcome_unknown": bool(res.get("outcome_unknown")),
                                       "error": str(res.get("error") or "Meta rejected the schedule request.")})
                    results.append({"page_id": pid, "page_name": p_info.get("page_name"), "success": False,
                                    "post_id": post_id, "meta_schedule_status": post_entry["meta_schedule_status"],
                                    "outcome_unknown": post_entry["outcome_unknown"], "error": post_entry["error"]})
                save_posts(scheduled_posts)
                continue
            post_entry = {
                "id": f"post_{int(time.time())}_{uuid.uuid4().hex[:6]}",
                "title": title,
                "content": caption,
                "page_id": pid,
                "page_name": p_info.get("page_name", pid),
                "type": "reel",
                "media_file": clip_filename,
                "first_comment": first_comment,
                "first_comment_snapshot": first_comment,
                "first_comment_profile_id": first_comment_profile_id,
                "first_comment_source": str(data.get("first_comment_source") or ("llm" if first_comment else "manual")),
                "first_comment_status": "ready" if first_comment else "not_configured",
                "first_comment_error": "",
                "article_url": str(data.get("article_url") or data.get("website_url") or "").strip(),
                "website_status": "ready" if str(data.get("article_url") or data.get("website_url") or "").strip() else ("pending_generation" if bool(data.get("auto_first_comment", False)) else "not_configured"),
                "website_error": "",
                "auto_first_comment": bool(data.get("auto_first_comment", False)),
                "use_llm_comment": bool(data.get("use_llm_comment", True)),
                "status": "scheduled",
                "publish_mode": "app_queue",
                "scheduled_time": scheduled_dt,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "token": p_token,
                "token_id": verified["token_id"],
                "token_group_id": token_group_id,
                "token_gap_seconds": stagger_minutes * 60,
            }
            scheduled_posts.append(post_entry)
            success_count += 1
            if bool(data.get("auto_first_comment", False)):
                from src.content_packages import attach_existing_package, enqueue_content_package
                # The attach helper persists to the posts ledger; save the new
                # row first so a reused ready package can update it immediately.
                save_posts(scheduled_posts)
                meta = get_clip_metadata(clip_filename) or {}
                package = attach_existing_package(
                    clip_filename=clip_filename, post_ids=[post_entry["id"]],
                    source_job_id=meta.get("job_id", ""), source_clip_id=meta.get("clip_index", ""),
                    needs_article=True, article_url=post_entry.get("article_url", ""),
                ) or enqueue_content_package(
                    clip_filename=clip_filename,
                    title=title,
                    summary=caption,
                    mode="auto",
                    post_ids=[post_entry["id"]],
                    article_url=post_entry.get("article_url", ""),
                    video_url=str(post_entry.get("video_url") or post_entry.get("youtube_url") or ""),
                    create_website_article=not post_entry.get("article_url"),
                    source_job_id=meta.get("job_id", ""), source_clip_id=meta.get("clip_index", ""),
                    first_comment_profile_id=first_comment_profile_id,
                )
                post_entry["content_package_id"] = package["id"]
                post_entry["content_package_status"] = package["status"]
                if package["status"] == "ready" and (package.get("result") or {}).get("caption"):
                    apply_ready_package_to_post(post_entry, package)
                if package["status"] == "queued":
                    scheduled_package_ids.add(package["id"])
            results.append({
                "page_id": pid,
                "page_name": p_info.get("page_name"),
                "success": True,
                "status": "SCHEDULED_LOCAL",
                "post_id": post_entry["id"],
                "scheduled_publish_time": curr_sched,
                "article_url": post_entry["article_url"],
                "website_status": post_entry["website_status"],
                "website_embed_status": "pending_generation" if post_entry.get("auto_first_comment") else "unknown",
                "website_error": post_entry["website_error"],
                "content_package_id": post_entry.get("content_package_id"),
            })
            continue

        # Immediate publish must use the same exact Page/token preflight as the
        # scheduler; never trust a stale cached page_token.
        immediate_preflight = preflight_pages([p_info], token_vault, page_manager)
        if not immediate_preflight.get("ok"):
            blocked = immediate_preflight.get("blocked") or {}
            results.append({
                "page_id": pid,
                "page_name": p_info.get("page_name"),
                "success": False,
                "error": blocked.get("action") or "Meta preflight failed",
                "code": blocked.get("code"),
                "stage": blocked.get("stage"),
                "reconnect_required": bool(blocked.get("reconnect_required", True)),
            })
            continue
        verified = immediate_preflight["ready"][0]
        p_token = verified["token"]

        # A prior ambiguous finish must not be replayed by another click.
        existing = next((item for item in load_posts() if
            str(item.get("page_id")) == str(pid) and
            (item.get("media_file") or item.get("clip_filename")) == clip_filename and
            item.get("status") in ("scheduled", "publishing", "processing", "published")
        ), None)
        if existing:
            results.append({"page_id": pid, "page_name": p_info.get("page_name"),
                            "success": False, "error": "Clip already queued, processing or posted for this Page; reconcile before retry.",
                            "duplicate_post_id": existing.get("id")})
            continue

        res = reel_poster.publish_reel(
            page_id=pid,
            page_token=p_token,
            video_path=str(video_path),
            description=full_description,
            first_comment=first_comment,
            schedule_time=curr_sched,
            token_id=verified["token_id"],
            reconcile_seconds=12,
        )

        facebook_id = res.get("video_id") or res.get("reel_id")
        if res.get("success") and facebook_id:
            comment_result = res.get("comment_result") or {}
            post_id = f"post_{int(time.time())}_{uuid.uuid4().hex[:6]}"
            comment_status = "posted" if comment_result.get("success") else ("ready" if first_comment else "not_configured")
            comment_queue_id = ""
            comment_error = str(comment_result.get("error") or "")
            if first_comment and not comment_result.get("success"):
                try:
                    from src.publisher.first_comment_queue import enqueue_first_comment
                    queued = enqueue_first_comment(
                        facebook_id, p_token, first_comment, int(time.time()) + 30,
                        token_id=verified["token_id"], post_id=post_id,
                        outcome_unknown=bool(comment_result.get("outcome_unknown")),
                    )
                    comment_status = "verification_pending" if queued.get("outcome_unknown") else ("pending_retry" if queued.get("success") else "queue_failed")
                    if queued.get("outcome_unknown"):
                        comment_error = "First Comment outcome unknown; queue is paused until Meta verification."
                    comment_queue_id = queued.get("queue_id") or ""
                    if not queued.get("success"):
                        comment_error = str(queued.get("error") or comment_error)
                except Exception as exc:
                    comment_status = "queue_failed"
                    comment_error = str(exc)
            success_count += 1
            p_info["total_posted"] = p_info.get("total_posted", 0) + 1
            pages_updated = True
            results.append({
                "page_id": pid,
                "page_name": p_info.get("page_name"),
                "success": True,
                "status": res.get("status"),
                "video_id": res.get("video_id"),
                "fb_url": res.get("fb_url"),
                "scheduled_publish_time": res.get("scheduled_publish_time"),
                "comment_result": comment_result,
                "first_comment_status": comment_status,
            })
            if not schedule_time:
                # Immediate publishes must appear in Post Management just like
                # worker-published scheduled posts, including a clickable Reel URL.
                immediate_posts = load_posts()
                immediate_posts.insert(0, {
                    "id": post_id,
                    "title": title,
                    "content": caption,
                    "page_id": pid,
                    "page_name": p_info.get("page_name", pid),
                    "type": "reel",
                    "media_file": clip_filename,
                    "first_comment": first_comment,
                    "article_url": article_url,
                    "website_status": "ready" if article_url else "not_configured",
                    "website_error": "",
                    "first_comment_status": comment_status,
                    "first_comment_error": comment_error,
                    "first_comment_queue_id": comment_queue_id,
                    "comment_id": comment_result.get("comment_id") or "",
                    "post_fb_id": facebook_id or "",
                    "fb_url": res.get("fb_url") or (
                        f"https://www.facebook.com/reel/{facebook_id}" if facebook_id else ""
                    ),
                    "status": "published",
                    "posted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "token_id": verified["token_id"],
                })
                save_posts(immediate_posts)
                try:
                    from web.scheduled_publisher import _record_posted_clip
                    _record_posted_clip(clip_filename)
                except Exception:
                    pass  # A local cleanup failure must never change a confirmed Meta result.
        elif res.get("processing") and (res.get("meta_post_id") or res.get("upload_video_id")):
            pending_posts = load_posts()
            pending_posts.insert(0, {
                "id": f"post_{int(time.time())}_{uuid.uuid4().hex[:6]}",
                "title": title, "content": caption, "page_id": pid,
                "page_name": p_info.get("page_name", pid), "type": "reel",
                "media_file": clip_filename, "first_comment": first_comment,
                "article_url": str(data.get("article_url") or data.get("website_url") or "").strip(),
                "status": "processing", "meta_post_id": str(res.get("meta_post_id") or ""),
                "meta_upload_video_id": str(res.get("upload_video_id") or ""),
                "meta_reconcile_attempts": 0, "meta_next_check_at": time.time() + 60,
                "retryable": False, "retry_stage": "meta_processing",
                "error": "Meta is processing; awaiting independent read-only verification. Do not retry.",
                "token_id": verified["token_id"],
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
            save_posts(pending_posts)
            results.append({"page_id": pid, "page_name": p_info.get("page_name"),
                            "success": False, "processing": True, "outcome_unknown": True,
                            "meta_post_id": str(res.get("meta_post_id") or ""), "error": "Meta processing; do not retry."})
        else:
            # Persist a failed direct publish so the operator can inspect the
            # exact Meta error in Post Management instead of losing it when the
            # request response closes. This row is never retried automatically.
            failure_post = {
                "id": f"post_{int(time.time())}_{uuid.uuid4().hex[:6]}",
                "title": title, "content": caption, "page_id": pid,
                "page_name": p_info.get("page_name", pid), "type": "reel",
                "media_file": clip_filename, "first_comment": first_comment,
                "article_url": article_url, "status": "failed",
                "retryable": bool(res.get("retryable", False)),
                "retry_stage": "facebook_publish",
                "error": str(res.get("error") or "Meta publish returned no object id; outcome is unknown and must be reconciled before retry."),
                "outcome_unknown": bool(res.get("outcome_unknown")),
                "token_id": verified["token_id"],
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            failed_posts = load_posts()
            failed_posts.insert(0, failure_post)
            save_posts(failed_posts)
            results.append({
                "page_id": pid,
                "page_name": p_info.get("page_name"),
                "success": False,
                "error": res.get("error") or "Meta publish returned no object id; outcome is unknown and must be reconciled before retry.",
                "outcome_unknown": bool(res.get("outcome_unknown") or (res.get("success") and not facebook_id)),
            })

    if pages_updated:
        page_manager.save_pages(pages)
    if not schedule_time and target_page_ids and len(results) == len(target_page_ids) and all(r.get("success") for r in results):
        try:
            from web.scheduled_publisher import remove_posted_clip_file
            current_posts = load_posts()
            if remove_posted_clip_file(clip_filename, current_posts):
                for post in current_posts:
                    if str(post.get("media_file") or "") == clip_filename and post.get("status") == "published":
                        post["local_video_deleted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                save_posts(current_posts)
        except Exception:
            pass
    if schedule_time and success_count:
        save_posts(scheduled_posts)
        prioritize_scheduled_packages(scheduled_package_ids)
        if scheduled_package_ids:
            start_content_package_worker()

    return jsonify({
        "success": success_count > 0 or any(result.get("processing") for result in results),
        "total_targets": len(target_page_ids),
        "success_count": success_count,
        "processing_count": sum(1 for result in results if result.get("processing")),
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
                cfg = json.load(f)
            video = dict(cfg.get("video_upload") or {})
            if str(video.get("method") or "").strip().lower() == "scp" and not any(
                str(video.get(key) or "").strip()
                for key in ("host", "username", "private_key_path", "remote_dir", "public_base_url")
            ):
                video["method"] = "cms"
                cfg["video_upload"] = video
            return cfg
        except Exception:
            pass
    return {"base_url": "", "username": "", "password": "", "video_upload": {"method": "cms", "port": 22}}

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
            "video_upload": cfg.get("video_upload") or {"method": "cms", "port": 22}
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
        service = WebsiteArticleService(WEBSITE_CFG_FILE)
        settings = service._video_settings()
        if settings.get("method") == "cms":
            connection = service.test_connection()
            return jsonify({"success": True, "method": "youtube_embed", "status": "embed_ready",
                            "authenticated": bool(connection.get("authenticated")),
                            "video_upload_supported": False, "requires_original_youtube": True,
                            "message": "CMS kết nối tốt. Video YouTube gốc sẽ được nhúng vào bài; ảnh được upload riêng. "
                                       "Video không có nguồn YouTube cần cấu hình SCP để lưu bản đầy đủ."})
        return jsonify(service.test_video_uploader())
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 502



@app.route("/api/posts/clear", methods=["POST"])
def api_clear_posts():
    from web.scheduled_publisher import _cycle_lock
    if not _cycle_lock.acquire(blocking=False):
        return jsonify({"success": False, "error": "App đang xử lý bài; thử lại sau ít giây."}), 409
    try:
        data = request.get_json(silent=True) or {}
        status_filter = data.get("status", "all") # 'all' or 'scheduled'
        
        posts = load_posts()
        if status_filter != "scheduled" and any(p.get("status") in ("meta_handoff", "publishing", "processing", "meta_scheduled") for p in posts):
            return jsonify({"success": False, "error": "Có bài đang giao hoặc đã giao Meta. Xóa lịch local không hủy lịch trên Meta."}), 409
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
    finally:
        _cycle_lock.release()

@app.route("/api/scheduler/status", methods=["GET"])
def api_scheduler_status():
    """Expose worker heartbeat so the UI can show stale/overdue warnings."""
    try:
        try:
            from web.scheduled_publisher import worker_status as _status, start_worker_thread as _start_worker
        except ImportError:
            from scheduled_publisher import worker_status as _status, start_worker_thread as _start_worker
        status = _status()
        if not status.get("thread_alive"):
            _start_worker(restart_dead=True)
            status = _status()
    except Exception as exc:
        try:
            from web.scheduled_publisher import sanitize_error
        except ImportError:
            from scheduled_publisher import sanitize_error
        return jsonify({"success": False, "error": sanitize_error(exc)}), 500

    posts = load_posts()
    now_dt = datetime.now()
    overdue = []
    for post in posts:
        if post.get("status") not in ("scheduled", "publishing"):
            continue
        raw_time = post.get("scheduled_time")
        if not raw_time:
            continue
        try:
            scheduled_dt = datetime.strptime(str(raw_time).replace("T", " ")[:19], "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue
        late_seconds = int((now_dt - scheduled_dt).total_seconds())
        if late_seconds > int(status.get("jitter_threshold_seconds", 120)):
            overdue.append({
                "id": post.get("id"),
                "title": post.get("title", ""),
                "page_name": post.get("page_name", ""),
                "status": post.get("status"),
                "scheduled_time": post.get("scheduled_time"),
                "late_seconds": late_seconds,
                "actionable": post.get("status") == "scheduled",
                "blocked_reason": (
                    "publish outcome unknown; reconcile before retry"
                    if post.get("status") == "publishing" else ""
                ),
            })
    status["overdue_count"] = len(overdue)
    status["overdue_posts"] = overdue[:50]
    status["success"] = True
    from multi_pc.publishing_settings import load_publishing_settings, MAX_POSTING_THREADS
    status.update(load_publishing_settings(POSTS_FILE.parent))
    status["max_posting_threads"] = MAX_POSTING_THREADS
    return jsonify(status)


@app.route("/api/publishing/settings", methods=["GET", "PUT"])
def api_publishing_settings():
    from multi_pc.publishing_settings import load_publishing_settings, save_publishing_settings, MAX_POSTING_THREADS
    try:
        settings = (save_publishing_settings(POSTS_FILE.parent, (request.get_json(silent=True) or {}).get("posting_threads"))
                    if request.method == "PUT" else load_publishing_settings(POSTS_FILE.parent))
        return jsonify({"success": True, "max_posting_threads": MAX_POSTING_THREADS, **settings})
    except (ValueError, TypeError) as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@app.route("/api/scheduler/run-due", methods=["POST"])
def api_scheduler_run_due():
    """Manual operator trigger to process overdue posts when a cycle was missed.

    Reuses the same claim/duplicate guards as the background worker; no forced
    final actions and no publish-approval bypass.
    """
    try:
        try:
            from web.scheduled_publisher import process_scheduled_posts_once
        except ImportError:
            from scheduled_publisher import process_scheduled_posts_once
        result = process_scheduled_posts_once()
        if result.get("busy"):
            return jsonify({
                "success": False,
                "busy": True,
                "error": "Worker đang đăng bài khác. Bài quá hạn vẫn nằm trong hàng chờ và sẽ được xử lý ở chu kỳ kế tiếp.",
            }), 409
        return jsonify({
            "success": True,
            "claimed": result.get("claimed", 0),
            "recovered": result.get("recovered", 0),
            "failed": result.get("failed", 0),
            "message": "Da xu ly cac bai den han.",
        })
    except Exception as exc:
        try:
            from web.scheduled_publisher import sanitize_error
        except ImportError:
            from scheduled_publisher import sanitize_error
        return jsonify({"success": False, "error": sanitize_error(exc)}), 500


def _inspect_post_meta(post):
    """Resolve the original saved credential rather than a Page's later default."""
    from web.meta_diagnostics import observation
    from web.meta_recovery import publishing_token_id
    entry = token_vault.get_token_by_id(publishing_token_id(post))
    mapping, error = page_manager.resolve_verified_mapping(post.get("page_id"), entry)
    if error or not mapping:
        return observation({"error": {"message": "Token gốc hoặc binding Page chưa được xác minh; hãy Sync Page đúng Token."}}, 409), None
    video_id = post.get("meta_upload_video_id") or post.get("meta_video_id")
    return reel_poster.inspect_reel(video_id, mapping["page_token"], mapping["token_id"]), mapping


@app.route("/api/posts/<post_id>/meta-diagnosis", methods=["GET"])
def api_post_meta_diagnosis(post_id):
    from web.meta_diagnostics import diagnose
    post = next((item for item in load_posts() if item.get("id") == post_id), None)
    if not post:
        return jsonify({"success": False, "error": "Không tìm thấy bài."}), 404
    seen, mapping = _inspect_post_meta(post)
    from web.meta_recovery import can_retry_existing, can_refresh_existing, recovery_credentials, publishing_token_id
    diagnostic = diagnose(post, seen)
    diagnostic["can_retry_existing"] = can_refresh_existing(post) and (
        can_retry_existing(post, seen) or seen.get("http_status") != 200 or bool(seen.get("error")))
    return jsonify({"success": True, "post_id": post_id, "title": post.get("title"),
                    "page_name": post.get("page_name"), "page_id": post.get("page_id"),
                    "observation": seen, "diagnosis": diagnostic,
                    "recovery_credentials": recovery_credentials(post, token_vault, page_manager),
                    "recovery_token_id": publishing_token_id(post)})


@app.route("/api/posts/<post_id>/recover-existing", methods=["POST"])
def api_recover_existing_post(post_id):
    from web.meta_recovery import (can_retry_existing, can_refresh_existing, refresh_page_credential,
                                  publishing_token_id, recovery_credentials)
    from web.scheduled_publisher import _cycle_lock, _resume_complete_upload, sanitize_error, _parse_scheduled_time
    from multi_pc.publishing_settings import credential_ready
    body = request.get_json(silent=True) or {}
    if body.get("confirm_existing_upload") is not True or not body.get("video_id"):
        return jsonify({"success": False, "error": "Cần xác nhận đúng video hiện có trước khi thử đăng lại."}), 400
    if not _cycle_lock.acquire(blocking=False):
        return jsonify({"success": False, "busy": True, "error": "App đang xử lý bài; chờ chu kỳ này hoàn tất rồi thử lại."}), 409
    try:
        posts = load_posts()
        post = next((p for p in posts if p.get("id") == post_id), None)
        if post is None:
            return jsonify({"success": False, "error": "Không tìm thấy bài."}), 404
        if str(post.get("meta_upload_video_id")) != str(body["video_id"]):
            return jsonify({"success": False, "error": "Meta ID đã thay đổi; hãy kiểm tra lại bài."}), 409
        if not can_refresh_existing(post):
            return jsonify({"success": False, "error": "Bài đã đăng hoặc Meta còn xử lý/chưa rõ kết quả; app tiếp tục đối soát ID cũ."}), 409
        current = datetime.now()
        started = _parse_scheduled_time(post.get("auto_finish_started_at"))
        if started is not None and current.timestamp() - started.timestamp() < 30:
            return jsonify({"success": False, "error": "Vừa thử đăng; chờ ít nhất 30 giây trước khi thử tiếp."}), 409
        selected = str(body.get("token_id") or publishing_token_id(post))
        allowed = {item["token_id"] for item in recovery_credentials(post, token_vault, page_manager)}
        if selected not in allowed:
            return jsonify({"success": False, "error": "Chọn Token gốc hoặc mapping đã xác minh cho đúng Page này."}), 409
        if not credential_ready(token_vault.get_token_by_id(selected)):
            return jsonify({"success": False, "error": "Token đang cooldown hoặc chưa hoạt động; hãy kiểm tra Token trong kho."}), 409
        credential, summary = refresh_page_credential(post, token_vault, page_manager, selected)
        if credential is None:
            return jsonify({"success": False, "error": summary["error"], "credential_check": summary}), 409
        # Re-read with the refreshed, same-Page credential before a remote write.
        seen = reel_poster.inspect_reel(post["meta_upload_video_id"], credential["token"], selected)
        if not can_retry_existing(post, seen):
            return jsonify({"success": False, "error": "Trạng thái Meta đã thay đổi; chưa gửi yêu cầu đăng lại."}), 409
        previous = publishing_token_id(post)
        if selected != str(post.get("token_id") or ""):
            post["meta_recovery_token_id"] = selected
        else:
            post.pop("meta_recovery_token_id", None)
        post["meta_credential_refresh"] = {**summary, "checked_at": current.isoformat()}
        if selected != previous:
            post.setdefault("meta_recovery_history", []).append({"from_token_id": previous, "to_token_id": selected,
                "at": current.isoformat(), "video_id": post["meta_upload_video_id"]})
        performed = _resume_complete_upload(post, seen, reel_poster, credential, posts, current, force_retry=True)
        if not performed:
            return jsonify({"success": False, "error": "Không đủ điều kiện phục hồi; giữ nguyên bài để tiếp tục đối soát."}), 409
        state = post.get("auto_finish_state")
        message = ("Đã đồng bộ quyền Page và gửi đăng video cũ; app đang xác minh kết quả." if state == "accepted" else
                   "Meta chưa xác nhận; app giữ nguyên video và đang đối soát." if state == "unknown" else
                   "Đã đồng bộ quyền Page nhưng Meta vẫn từ chối: " + sanitize_error(post.get("auto_finish_error")))
        return jsonify({"success": True, "accepted": state == "accepted", "state": state, "message": message,
                        "video_id": post["meta_upload_video_id"], "credential_check": summary})
    except Exception as exc:
        return jsonify({"success": False, "error": sanitize_error(exc)}), 500
    finally:
        _cycle_lock.release()


@app.route("/api/posts/<post_id>/finish-existing-upload", methods=["POST"])
def api_finish_existing_upload(post_id):
    from web.meta_diagnostics import diagnose, safe_error
    from web.scheduled_publisher import _cycle_lock
    from multi_pc.publishing_settings import credential_ready
    body = request.get_json(silent=True) or {}
    if body.get("confirm_existing_upload") is not True or not body.get("video_id"):
        return jsonify({"success": False, "error": "Cần xác nhận hoàn tất đúng upload hiện có."}), 400
    if not _cycle_lock.acquire(blocking=False):
        return jsonify({"success": False, "error": "Worker đang chạy; hãy kiểm tra lại sau chu kỳ này."}), 409
    try:
        posts = load_posts()
        post = next((item for item in posts if item.get("id") == post_id), None)
        if not post:
            return jsonify({"success": False, "error": "Không tìm thấy bài."}), 404
        if str(post.get("meta_upload_video_id") or "") != str(body["video_id"]):
            return jsonify({"success": False, "error": "Meta upload ID đã khác; hãy kiểm tra lại bài."}), 409
        seen, mapping = _inspect_post_meta(post)
        diagnostic = diagnose(post, seen)
        replacement_schedule = body.get("schedule_time")
        if replacement_schedule is not None:
            if not diagnostic.get("can_reschedule_existing"):
                return jsonify({"success": False, "error": "Upload này không đủ điều kiện chọn giờ mới.", "diagnosis": diagnostic}), 409
            from multi_pc.meta_scheduling import parse_meta_schedule_time
            try:
                replacement_schedule = parse_meta_schedule_time(replacement_schedule)
            except ValueError as exc:
                return jsonify({"success": False, "error": str(exc)}), 400
            diagnostic = diagnose({**post, "meta_scheduled_publish_time": replacement_schedule}, seen)
        if not diagnostic["can_finish_existing"] or not mapping:
            return jsonify({"success": False, "error": diagnostic["message"], "diagnosis": diagnostic}), 409
        if not credential_ready(token_vault.get_token_by_id(mapping["token_id"])):
            return jsonify({"success": False, "error": "Token đang cooldown hoặc bị hạn chế; chờ trước khi gửi Finish."}), 409
        if any(item.get("id") != post_id and item.get("status") == "publishing" and
               (item.get("token_id") == post.get("token_id") or item.get("page_id") == post.get("page_id")) for item in posts):
            return jsonify({"success": False, "error": "Token/Page đang có upload khác; hãy chờ hoàn tất."}), 409
        native = post.get("publish_mode") == "meta_scheduled" or bool(post.get("meta_scheduled_publish_time"))
        schedule = (post.get("meta_scheduled_publish_time") or post.get("scheduled_time")) if native else None
        description = post.get("meta_description_snapshot") or f"{post.get('title') or ''}\n\n{post.get('content') or ''}"
        from src.english_text import assert_english
        try:
            assert_english(description, "Reel description")
        except ValueError as exc:
            return jsonify({"success": False, "error": str(exc)}), 409
        if replacement_schedule is not None:
            post.setdefault("original_scheduled_time", post.get("scheduled_time"))
            schedule = replacement_schedule
            post.update(meta_scheduled_publish_time=schedule,
                        scheduled_time=datetime.fromtimestamp(schedule).strftime("%Y-%m-%d %H:%M:%S"),
                        meta_schedule_status="verification_pending")
        post.update(meta_finish_recovery_attempts=1, meta_finish_recovery_state="requesting",
                    meta_finish_recovery_started_at=datetime.now().astimezone().isoformat(),
                    meta_observation=seen, outcome_unknown=True, retryable=False)
        # Persist the claim before a remote write. A crash leaves a durable fence
        # that disables a second Finish and every generic re-upload path.
        try:
            save_posts(posts)
        except Exception:
            return jsonify({"success": False, "error": "Không thể lưu khóa an toàn trước khi gửi Finish; Meta chưa được gọi."}), 500
        try:
            result = reel_poster.finish_existing_reel(post["page_id"], mapping["page_token"], post["meta_upload_video_id"],
                description, schedule_time=schedule, token_id=mapping["token_id"])
        except Exception:
            result = {"accepted": False, "state": "unknown", "error": "Phản hồi Finish chưa rõ; tiếp tục đối soát đúng Meta ID."}
        post.update(meta_finish_recovery_state=result["state"], meta_finish_recovery_error=safe_error(result.get("error")),
                    meta_next_check_at=time.time() + 30)
        post["meta_diagnosis"] = diagnose(post)
        try:
            save_posts(posts)
        except Exception:
            return jsonify({"success": True, "accepted": False, "state": "unknown", "post_id": post_id,
                            "video_id": post["meta_upload_video_id"],
                            "message": "Đã gửi yêu cầu một lần nhưng chưa lưu được phản hồi; giữ nguyên Meta ID và không gửi lại."}), 202
        return jsonify({"success": True, "accepted": bool(result.get("accepted")), "state": result["state"],
                        "post_id": post_id, "video_id": post["meta_upload_video_id"],
                        "message": "Meta đã nhận yêu cầu hoàn tất; chờ xác minh xuất bản." if result.get("accepted") else
                                   safe_error(result.get("error") or "Meta chưa xác nhận Finish.")})
    finally:
        _cycle_lock.release()


@app.route("/api/posts", methods=["GET"])
def api_get_posts():
    from web.meta_handoff import handoff_eligibility
    from web.dashboard import post_bucket
    from web.meta_diagnostics import diagnose
    posts = load_posts()
    from web.token_audit import token_audit
    token_audit(posts, page_manager.list_pages(), token_vault.list_tokens(mask=True), load_token_groups())
    for post in posts:
        post["post_bucket"] = post_bucket(post)
        if post.get("status") == "processing":
            post["meta_diagnosis"] = diagnose(post)
        post["can_handoff_meta"], post["meta_handoff_blocked_reason"] = handoff_eligibility(post, OUTPUT_DIR)
        media_file = post.get("media_file") or post.get("clip_filename")
        if media_file:
            post["local_video_url"] = f"/api/clips/play/{media_file}"
            post["local_download_url"] = f"/api/clips/play/{media_file}?download=1"
            post["local_video_available"] = (OUTPUT_DIR / Path(media_file).name).is_file()
            post["local_video_removed_after_publish"] = (
                post.get("status") == "published" and not post["local_video_available"]
            )
        post["article_url"] = str(post.get("article_url") or post.get("website_url") or "").strip()
        package = post.get("content_package") if isinstance(post.get("content_package"), dict) else {}
        item_embed = post.get("website_embed_status") or post.get("embed_status") or package.get("embed_status") or ""
        youtube_id = post.get("youtube_id") or package.get("youtube_id") or ""
        video_url = post.get("video_url") or package.get("video_url") or ""
        post["website_embed_status"] = item_embed or ("ready" if (youtube_id or video_url) and post.get("website_status") == "ready" else ("pending_generation" if post.get("website_status") in ("pending_generation", "generating") else "unknown"))
        post["youtube_id"] = youtube_id
        facebook_id = post.get("post_fb_id") or post.get("reel_id")
        if facebook_id and not post.get("fb_url"):
            post["fb_url"] = f"https://www.facebook.com/reel/{facebook_id}"
    # Sắp xếp bài mới lên lịch / mới đăng lên đầu danh sách (Newest First)
    def _sort_key(p):
        # Ưu tiên sắp xếp theo thời điểm tạo bài hoặc lên lịch
        c_at = p.get("created_at", "")
        s_at = p.get("scheduled_time", "")
        p_id = p.get("id", "")
        return (c_at, s_at, p_id)
    posts = sorted(posts, key=_sort_key, reverse=True)
    # Raw publishing credentials are server-side data, never UI payloads.
    return jsonify([{key: value for key, value in post.items() if key not in ("token", "page_token", "access_token")} for post in posts])


@app.route("/api/posts/token-audit", methods=["GET"])
def api_posts_token_audit():
    from web.token_audit import token_audit
    return jsonify({"success": True, **token_audit(load_posts(), page_manager.list_pages(),
                                                token_vault.list_tokens(mask=True), load_token_groups())})


@app.route("/api/posts/handoff-meta", methods=["POST"])
def api_handoff_posts_to_meta():
    from web.meta_handoff import queue_handoffs
    from web.scheduled_publisher import _cycle_lock
    data = request.get_json(silent=True) or {}
    post_ids = data.get("post_ids")
    if not isinstance(post_ids, list) or not post_ids or len(post_ids) > 500 or any(not isinstance(pid, str) or not pid.strip() for pid in post_ids):
        return jsonify({"success": False, "error": "Chọn từ 1 đến 500 bài cần giao Meta."}), 400
    if not _cycle_lock.acquire(blocking=False):
        return jsonify({"success": False, "busy": True, "error": "App đang xử lý bài khác; thử lại sau ít giây."}), 409
    try:
        posts = load_posts()
        results = queue_handoffs(posts, post_ids, OUTPUT_DIR, token_vault, page_manager)
        accepted = sum(item["accepted"] for item in results)
        if accepted:
            save_posts(posts)
        return jsonify({"success": True, "accepted_count": accepted,
                        "skipped_count": len(results) - accepted, "results": results})
    finally:
        _cycle_lock.release()

@app.route("/api/posts/health", methods=["GET"])
def api_posts_health():
    """Expose an explicit warning when the post ledger was cleared independently.

    Content packages and posted_clips are retained after a queue wipe, so an empty
    /api/posts response must not look like a clean first run to the operator.
    """
    posts = load_posts()
    posted_file = POSTS_FILE.parent / "posted_clips.json"
    posted_count = 0
    if posted_file.exists():
        try:
            value = json.loads(posted_file.read_text(encoding="utf-8"))
            posted_count = len(value) if isinstance(value, list) else 0
        except Exception:
            pass
    package_count = 0
    try:
        from src.content_packages import list_packages
        package_count = sum(1 for item in list_packages() if item.get("post_ids"))
    except Exception:
        pass
    recovered_count = sum(1 for post in posts if post.get("recovered_from_meta"))
    suspected = (not posts or recovered_count == len(posts)) and (posted_count > 0 or package_count > 0)
    return jsonify({"success": True, "ledger_empty": not posts,
                    "ledger_empty_suspected": suspected,
                    "ledger_incomplete_suspected": suspected,
                    "recovered_meta_count": recovered_count,
                    "posted_clip_count": posted_count,
                    "linked_package_count": package_count,
                    "message": (f"Đã phục hồi {recovered_count} Reel từ Meta, nhưng lịch đăng cũ đã mất. Không đăng lại tự động để tránh trùng bài." if suspected and recovered_count else
                                "Post ledger đang rỗng nhưng dữ liệu Content Studio/đã đăng vẫn còn; không đăng lại tự động." if suspected else "")})

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
        "first_comment_status": data.get("first_comment_status") or ("ready" if data.get("first_comment") else "not_configured"),
        "first_comment_error": data.get("first_comment_error", ""),
        "article_url": data.get("article_url") or data.get("website_url") or "",
        "website_status": data.get("website_status") or ("ready" if (data.get("article_url") or data.get("website_url")) else "not_configured"),
        "website_error": data.get("website_error", ""),
        "post_fb_id": data.get("post_fb_id", ""),
        "fb_url": data.get("fb_url") or data.get("url", ""),
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
    from web.scheduled_publisher import _cycle_lock
    if not _cycle_lock.acquire(blocking=False):
        return jsonify({"success": False, "error": "App đang xử lý bài; thử lại sau ít giây."}), 409
    try:
        posts = load_posts()
        post = next((p for p in posts if p.get("id") == post_id), None)
        if post and post.get("status") in ("meta_handoff", "publishing", "processing", "meta_scheduled"):
            return jsonify({"success": False, "error": "Bài đang giao hoặc đã giao Meta. Xóa lịch local không hủy lịch trên Meta."}), 409
        posts = [p for p in posts if p.get("id") != post_id]
        save_posts(posts)
        return jsonify({"success": True})
    finally:
        _cycle_lock.release()


@app.route("/api/posts/<post_id>/retry-website", methods=["POST"])
def api_retry_post_website(post_id):
    """Retry only CMS preparation; never publish or reschedule Facebook."""
    posts = load_posts()
    post = next((item for item in posts if item.get("id") == post_id), None)
    if not post:
        return jsonify({"success": False, "error": "Không tìm thấy bài đã lên lịch"}), 404
    if post.get("article_url") and post.get("website_status") == "ready":
        return jsonify({"success": True, "post": post, "already_ready": True})

    fields = prepare_website_article_for_schedule(
        post.get("media_file") or post.get("clip_filename"),
        post.get("title", ""),
        article_url=post.get("article_url"),
        first_comment=post.get("first_comment"),
        auto_first_comment=True,
        use_llm_comment=post.get("use_llm_comment", True),
    )
    post.update(fields)
    post["website_retried_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_posts(posts)
    if post.get("website_status") != "ready":
        return jsonify({"success": False, "error": post.get("website_error"), "post": post}), 502
    return jsonify({"success": True, "post": post})


@app.route("/api/distribute/batch", methods=["POST"])
def api_distribute_batch():
    from src.content_packages import scheduled_video_path
    from src.publisher.schedule_media import selected_video, source_identity, stage_video
    import re
    from datetime import datetime, timedelta
    data = request.json or {}
    blocked = _ensure_recent_meta_health()
    if blocked is not None:
        return blocked
    group_id = data.get("group_id")
    token_group_id = str(data.get("token_group_id") or "").strip()
    clip_filenames = data.get("clip_filenames", [])
    if not isinstance(clip_filenames, list) or any(not isinstance(fn, str) for fn in clip_filenames):
        return jsonify({"success": False, "code": "invalid_video_path", "error": "Clip selections must be a list of filenames"}), 400
    posts_per_page = int(data.get("posts_per_page", 1))
    stagger_minutes = max(1, int(data.get("stagger_minutes", 15)))
    from multi_pc.publishing_settings import load_publishing_settings, save_publishing_settings
    try:
        posting_threads = (save_publishing_settings(POSTS_FILE.parent, data["posting_threads"])
                           if "posting_threads" in data else load_publishing_settings(POSTS_FILE.parent))["posting_threads"]
    except (ValueError, TypeError) as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    publish_mode = str(data.get("publish_mode") or "app_queue")
    if publish_mode not in ("app_queue", "meta_scheduled"):
        return jsonify({"success": False, "error": "Chế độ đăng không hợp lệ."}), 400
    requested_start = str(data.get("start_time") or "").strip()
    start_dt = None
    if requested_start:
        try:
            start_dt = datetime.fromisoformat(requested_start)
            if start_dt.tzinfo is not None:
                start_dt = start_dt.astimezone().replace(tzinfo=None)
        except ValueError:
            return jsonify({"success": False, "code": "invalid_start_time", "error": "Start time must be ISO date/time"}), 400
        if start_dt <= datetime.now() + timedelta(seconds=5):
            return jsonify({"success": False, "code": "start_time_in_past", "error": "Start time must be in the future"}), 400
    auto_first_comment = data.get("auto_first_comment", True)
    use_llm_comment = data.get("use_llm_comment", True)
    configured_first_comment = str(data.get("first_comment") or "").strip()
    profile_store = load_profile_store(FIRST_COMMENT_PROFILES_FILE)
    first_comment_profile_id = str(data.get("first_comment_profile_id") or profile_store.get("default_profile_id") or "builtin_general")
    if first_comment_profile_id not in {str(profile.get("id")) for profile in profile_store.get("profiles", [])}:
        return jsonify({"success": False, "code": "first_comment_profile_missing", "error": "First Comment profile not found."}), 400
    configured_website_url = str(data.get("article_url") or data.get("website_url") or "").strip()
    if configured_website_url and configured_website_url not in configured_first_comment:
        configured_first_comment = f"{configured_first_comment}\n{configured_website_url}".strip()
    if not auto_first_comment and not configured_website_url:
        return jsonify({
            "success": False,
            "error": "Cần link bài Website hoặc bật tự động tạo bài để First Comment luôn có link.",
            "code": "website_article_required",
        }), 400

    if not group_id:
        return jsonify({"error": "Thiếu group_id"}), 400

    groups = page_manager.list_groups()
    group = next((g for g in groups if g.get("id") == group_id), None)
    if not group:
        return jsonify({"error": "Không tìm thấy Nhóm Fanpage"}), 404

    page_ids = group.get("page_ids", [])
    if not token_group_id:
        token_group_id = next((str(g["id"]) for g in load_token_groups()
                               if str(g.get("page_group_id") or "") == str(group_id)), "")
    if token_group_id:
        token_group = next((g for g in load_token_groups() if str(g.get("id")) == token_group_id), None)
        if not token_group:
            return jsonify({"success": False, "error": "Token group not found"}), 404
        # Explicit posting scope; page group still supplies schedule/folder.
        allowed = {str(pid) for pid in group.get("page_ids", [])}
        page_ids = [pid for pid in token_group.get("page_ids", []) if str(pid) in allowed]
        if not page_ids:
            return jsonify({"success": False, "error": "No Pages shared by the Page group and Token group snapshot"}), 400
    if not page_ids:
        return jsonify({"error": "Nhóm chưa có Fanpage nào được thêm"}), 400

    pages = page_manager.list_pages()
    # Group records created by older builds can store numeric IDs while the
    # synced page registry stores strings. Normalize before preflight; silently
    # dropping a missing page would otherwise produce a misleading schedule.
    page_ids = [str(pid).strip() for pid in page_ids if str(pid).strip()]
    page_map = {str(p.get("page_id")): p for p in pages if p.get("page_id")}
    missing_page_ids = [pid for pid in page_ids if pid not in page_map]
    if missing_page_ids:
        return jsonify({
            "success": False,
            "error": "Preflight quy?n dang b?i th?t b?i",
            "ok": False,
            "page_id": missing_page_ids[0],
            "code": "missing_page",
            "stage": "mapping",
            "action": "Sync l?i danh s?ch Page t? credential tr??c khi l?n l?ch.",
            "reconnect_required": True,
        }), 400
    posts = load_posts()

    # Verify exact page/token binding and publish capability before accepting any
    # schedule; a stale or cross-bound credential must never reach the queue.
    preflight = preflight_pages(
        [page_in_token_group(page_map[pid], token_group) if token_group_id else page_map[pid] for pid in page_ids],
        token_vault,
        page_manager,
    )
    if not preflight.get("ok"):
        return jsonify({"success": False, "error": 'Preflight quyền đăng bài thất bại', **preflight["blocked"]}), 400

    if token_group_id:
        allowed_tokens = {str(tid) for tid in token_group.get("token_ids", [])}
        outside = [ready["page_id"] for ready in preflight["ready"] if str(ready["token_id"]) not in allowed_tokens]
        if outside:
            return jsonify({"success": False, "error": "Page is not bound to a verified Token in the selected group",
                            "stage": "mapping", "page_ids": outside}), 409
    resolved_page_tokens = {ready["page_id"]: ready["token"] for ready in preflight["ready"]}
    verified_token_ids = {ready["page_id"]: ready["token_id"] for ready in preflight["ready"]}

    sched_cfg = group.get("schedule_config") or {}
    group_times = sched_cfg.get("times") or ["11:30", "19:30"]
    group_stagger = max(1, int(sched_cfg.get("stagger_minutes") or stagger_minutes))
    scheduled_offsets = paced_offsets_by_token(
        [verified_token_ids[pid] for pid in page_ids],
        global_seconds=0,
        token_seconds=group_stagger * 60,
    )

    configured_folder = str(group.get("folder_binding") or group.get("folder_path") or "").strip()
    folder_path = Path(configured_folder or str(OUTPUT_DIR)).expanduser()
    if not folder_path.is_dir():
        legacy_default = str(folder_path).replace("/", "\\").lower().rstrip("\\") == r"d:\highlight_video_studio\output"
        if legacy_default and OUTPUT_DIR.is_dir():
            folder_path = OUTPUT_DIR
            saved_groups = page_manager.list_groups()
            for saved_group in saved_groups:
                if str(saved_group.get("id")) == str(group_id):
                    saved_group["folder_binding"] = str(OUTPUT_DIR)
                    saved_group["folder_path"] = str(OUTPUT_DIR)
                    page_manager.save_groups(saved_groups)
                    break
        else:
            return jsonify({"success": False, "code": "missing_output_folder",
                            "error": f"Configured schedule clip folder does not exist: {folder_path}"}), 400
    folder_path = folder_path.resolve()
    canonical_output = OUTPUT_DIR.resolve()
    if not canonical_output.is_dir():
        return jsonify({"success": False, "code": "missing_output_folder", "error": "Canonical output folder is missing"}), 400

    posted_file = BASE_DIR / "posted_clips.json"
    posted_set = set()
    if posted_file.exists():
        try:
            records = json.loads(posted_file.read_text(encoding="utf-8"))
            for record in records if isinstance(records, list) else []:
                if isinstance(record, str):
                    posted_set.add(record)
                elif isinstance(record, dict):
                    posted_set.update(str(record.get(key)) for key in ("source_video_path", "media_file", "clip_filename") if record.get(key))
        except Exception:
            posted_set = set()

    handled_posts = [p for p in posts if p.get("status") in ("scheduled", "publishing", "processing") or
                     (p.get("status") == "published" and (p.get("post_fb_id") or p.get("reel_id")))]
    queued_clips = {str(p.get(key)) for p in handled_posts for key in ("media_file", "source_video_path") if p.get(key)}

    available_clips = []
    if clip_filenames:
        for fn in clip_filenames:
            try:
                candidate = selected_video(folder_path, fn)
            except (ValueError, FileNotFoundError, OSError) as exc:
                return jsonify({"success": False, "code": "invalid_video_path", "error": str(exc)}), 400
            available_clips.append(candidate)
    else:
        for p in sorted(folder_path.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                available_clips.append(selected_video(folder_path, p))
            except (ValueError, FileNotFoundError, OSError):
                continue

    # Compare source identities, never bare basenames from unrelated folders.
    seen_sources = set()
    filtered = []
    for candidate in available_clips:
        identity = source_identity(candidate)
        canonical_name = candidate.name if folder_path == canonical_output else None
        if identity in seen_sources or identity in posted_set or identity in queued_clips:
            continue
        if canonical_name and (canonical_name in posted_set or canonical_name in queued_clips):
            continue
        seen_sources.add(identity)
        filtered.append(candidate)
    available_clips = filtered

    if not available_clips:
        return jsonify({"error": "Không còn video clip mới nào chưa đăng/chưa hẹn để phân bổ! Hãy render thêm hoặc kiểm tra thư mục nguồn."}), 400

    # Prefer clips whose Content Studio package already has a verified CMS URL
    # and a First Comment containing that exact URL. This keeps scheduled Pages
    # from reaching Facebook before the website/comment assets are ready.
    try:
        from src.content_packages import list_packages
        package_rows = list_packages()
        def package_priority(path):
            def matches_path(package):
                raw = str(package.get("clip_filename") or "").strip()
                if not raw:
                    return False
                package_path = Path(raw)
                if folder_path == canonical_output:
                    return package_path.name == Path(path).name
                return package_path.is_absolute() and package_path.resolve() == Path(path).resolve()
            matches = [p for p in package_rows if matches_path(p)]
            for package in matches:
                result = package.get("result") or {}
                url = str(package.get("article_url") or "").strip()
                comment = str(result.get("first_comment") or "")
                if (package.get("status") == "ready" and package.get("website_status") == "ready"
                        and url and url in comment):
                    return 0
            return 1
        available_clips.sort(key=package_priority)
    except Exception:
        pass

    # Stage before writing queue rows: a failed source must not leave a partial schedule.
    staged_clips = []
    try:
        for source_clip in available_clips[:min(len(available_clips), posts_per_page * len(page_ids))]:
            if folder_path == canonical_output:
                clip_fn = str(scheduled_video_path(OUTPUT_DIR, source_clip).relative_to(canonical_output))
                source_sha = ""
                source_path = source_identity(source_clip)
            else:
                clip_fn, source_sha, source_path = stage_video(source_clip, OUTPUT_DIR)
            if clip_fn not in posted_set and clip_fn not in queued_clips:
                staged_clips.append((source_clip, clip_fn, source_sha, source_path))
    except (ValueError, FileNotFoundError, OSError) as exc:
        return jsonify({"success": False, "code": "invalid_video_path", "error": str(exc)}), 400
    available_clips = staged_clips
    if not available_clips:
        return jsonify({"success": False, "code": "no_new_clips", "error": "No unused clips in configured folder"}), 400

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

        if start_dt is not None:
            slot_base_dt = start_dt + timedelta(days=slot_idx)
        else:
            target_date = now_ts.date()
            slot_base_dt = datetime(target_date.year, target_date.month, target_date.day, th, tm, 0)
            if slot_base_dt <= now_ts:
                slot_base_dt += timedelta(days=1)

        for idx, pid in enumerate(page_ids):
            if clip_idx >= len(available_clips):
                break

            source_clip, clip_fn, source_sha, source_path = available_clips[clip_idx]
            clip_idx += 1

            p_info = page_map.get(pid, {})
            page_token = resolved_page_tokens[pid]

            post_id = f"post_{int(time.time())}_{uuid.uuid4().hex[:6]}"
            sched_dt = slot_base_dt + timedelta(seconds=scheduled_offsets[idx])
            sched_time_str = sched_dt.strftime("%Y-%m-%d %H:%M:%S")
            if publish_mode == "meta_scheduled":
                from multi_pc.meta_scheduling import parse_meta_schedule_time, MetaScheduleTimeError
                try:
                    parse_meta_schedule_time(sched_time_str)
                except MetaScheduleTimeError as exc:
                    return jsonify({"success": False, "code": exc.code, "error": str(exc)}), 400

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
                "source_video_path": source_path,
                "source_sha256": source_sha,
                "article_url": configured_website_url,
                "website_status": "ready" if configured_website_url else ("pending_generation" if auto_first_comment else "not_configured"),
                "website_error": "",
                "first_comment": configured_first_comment,
                "first_comment_snapshot": configured_first_comment,
                "first_comment_profile_id": first_comment_profile_id,
                "first_comment_source": "manual" if configured_first_comment else "pending",
                "first_comment_status": "ready" if configured_first_comment else "not_configured",
                "first_comment_error": "",
                "auto_first_comment": bool(auto_first_comment),
                "use_llm_comment": bool(use_llm_comment),
                "status": "scheduled",
                "publish_mode": "app_queue",
                "requested_publish_mode": publish_mode,
                "meta_schedule_status": "waiting_content" if publish_mode == "meta_scheduled" else "",
                "scheduled_time": sched_time_str,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "token": page_token,
                "token_id": verified_token_ids.get(pid, ""),
                "token_group_id": token_group_id,
                "token_gap_seconds": group_stagger * 60,
            }
            posts.append(post_entry)
            assigned_clips.append(clip_fn)
            scheduled_count += 1

    save_posts(posts)
    # Content packages run in the background queue; schedule creation never waits on
    # the LLM or the CMS.
    if scheduled_count:
        from src.content_packages import attach_existing_package, enqueue_content_package
        scheduled_package_ids = set()
        for post_entry in posts[-scheduled_count:]:
            meta = get_clip_metadata(post_entry["media_file"]) or {}
            package = attach_existing_package(
                clip_filename=post_entry["media_file"], post_ids=[post_entry["id"]],
                source_job_id=meta.get("job_id", ""), source_clip_id=meta.get("clip_index", ""),
                needs_article=bool(auto_first_comment), article_url=post_entry.get("article_url", ""),
            ) or enqueue_content_package(
                clip_filename=post_entry["media_file"],
                title=post_entry["title"],
                summary=str(post_entry.get("content") or ""),
                mode="auto" if use_llm_comment else "no_llm",
                post_ids=[post_entry["id"]],
                article_url=post_entry.get("article_url", ""),
                video_url=str(post_entry.get("video_url") or post_entry.get("youtube_url") or ""),
                create_website_article=bool(auto_first_comment) and not post_entry.get("article_url"),
                source_job_id=meta.get("job_id", ""), source_clip_id=meta.get("clip_index", ""),
                first_comment_profile_id=first_comment_profile_id,
            )
            post_entry["content_package_id"] = package["id"]
            post_entry["content_package_status"] = package["status"]
            if package["status"] == "ready" and (package.get("result") or {}).get("caption"):
                apply_ready_package_to_post(post_entry, package)
            if package["status"] == "queued":
                scheduled_package_ids.add(package["id"])
        save_posts(posts)
        prioritize_scheduled_packages(scheduled_package_ids)
        if scheduled_package_ids:
            start_content_package_worker()
    package_sources = {}
    package_statuses = {}
    for entry in posts[-scheduled_count:] if scheduled_count else []:
        source = str(entry.get("content_package_source") or "pending")
        status = str(entry.get("content_package_status") or "pending")
        package_sources[source] = package_sources.get(source, 0) + 1
        package_statuses[status] = package_statuses.get(status, 0) + 1
    return jsonify({
        "success": True,
        "scheduled_count": scheduled_count,
        "posts_per_page": posts_per_page,
        "website_failed_count": 0,
        "content_package_sources": package_sources,
        "content_package_statuses": package_statuses,
        "content_package_ready": package_statuses.get("ready", 0),
        "content_package_pending": sum(value for key, value in package_statuses.items() if key in ("queued", "running", "pending")),
        "content_package_llm": package_sources.get("llm", 0),
        "content_package_fallback": sum(value for key, value in package_sources.items() if key.startswith("no_llm")),
        "posting_threads": posting_threads,
        "schedule_recommendation": {
            **posting_schedule_recommendation(
                threads=posting_threads, pages=len(page_ids), window_minutes=group_stagger
            ),
            "actual_estimated_minutes": round(max(scheduled_offsets, default=0) / 60, 1),
            "distinct_tokens": len(set(verified_token_ids.values())),
        },
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


@app.route("/api/schedule/recommendation", methods=["GET"])
def api_schedule_recommendation():
    threads = request.args.get("threads", 10)
    pages = request.args.get("pages", 100)
    window = request.args.get("window_minutes", 15)
    try:
        recommendation = posting_schedule_recommendation(
            threads=int(threads), pages=int(pages), window_minutes=int(window)
        )
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "threads/pages/window_minutes must be integers"}), 400
    return jsonify({"success": True, "recommendation": recommendation})



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

@app.route("/api/queue/concurrency", methods=["GET", "POST"])
def api_queue_concurrency():
    global CONCURRENCY_MODE, MAX_CONCURRENT_JOBS
    if request.method == "GET":
        return jsonify({
            "mode": CONCURRENCY_MODE,
            "concurrency": MAX_CONCURRENT_JOBS,
            "auto_concurrency": AUTO_CONCURRENT_JOBS,
            "max_allowed": HARD_MAX_CONCURRENT_RENDERS,
            "active": len(ACTIVE_JOB_IDS),
            "semantics": "simultaneous render jobs; yt-dlp download fragments are unchanged",
        })

    data = request.get_json(silent=True) or {}
    try:
        mode, selected = resolve_concurrency(
            data.get("mode", "auto"),
            data.get("manual_concurrency", data.get("concurrency")),
            AUTO_CONCURRENT_JOBS,
            maximum=HARD_MAX_CONCURRENT_RENDERS,
        )
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    # Changing the limit cannot cancel or duplicate work. Lowering it only
    # affects future leases; already-running jobs finish normally.
    with QUEUE_LOCK:
        CONCURRENCY_MODE = mode
        MAX_CONCURRENT_JOBS = selected
        active = len(ACTIVE_JOB_IDS)
    return jsonify({
        "success": True,
        "mode": mode,
        "concurrency": selected,
        "auto_concurrency": AUTO_CONCURRENT_JOBS,
        "max_allowed": HARD_MAX_CONCURRENT_RENDERS,
        "active": active,
        "semantics": "simultaneous render jobs; yt-dlp download fragments are unchanged",
    })


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
        "concurrency_mode": CONCURRENCY_MODE,
        "auto_concurrency": AUTO_CONCURRENT_JOBS,
        "max_concurrent_allowed": HARD_MAX_CONCURRENT_RENDERS,
        "active": len(ACTIVE_JOB_IDS),
        "queued": queued_count,
        "running": running_count,
        "completed": completed_count,
        "error": error_count,
        "total": len(all_jobs)
    })

@app.route("/api/queue/pause", methods=["POST"])
def api_queue_pause():
    set_render_queue_pause(True)
    return jsonify({"success": True, "is_paused": True, "message": "Đã tạm dừng nhận link mới từ hàng đợi."})

@app.route("/api/queue/resume", methods=["POST"])
def api_queue_resume():
    set_render_queue_pause(False)
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

    # 2. Cập nhật token: only select a discovery-backed binding for this Page.
    if token_id:
        matched_tok = next((t for t in tokens if str(t.get("id")) == token_id), None)
        if not matched_tok:
            return jsonify({"success": False, "error": "Token không tồn tại trong Vault"}), 404
        binding = (target_page.get("token_bindings") or {}).get(token_id)
        if not binding or str(binding.get("verified_page_id") or "") != page_id:
            return jsonify({
                "success": False,
                **resolve_page_token({**target_page, "token_id": token_id}, token_vault, page_manager),
            }), 409
        target_page["token_id"] = token_id
        target_page["token_name"] = matched_tok.get("name", "System User")
        target_page["page_token"] = binding.get("page_token", "")
        target_page["mapping_status"] = "VERIFIED"
        target_page["mapping_verified_at"] = binding.get("verified_at", "")
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
    token_entry = token_vault.get_token_by_id(token_id) if token_id else None
    if token_id and not token_entry:
        return jsonify({"error": "Token không tồn tại trong Vault"}), 404
    updated = False
    for p in pages:
        if str(p.get("page_id")) == page_id:
            binding = (p.get("token_bindings") or {}).get(token_id) if token_entry else None
            if token_entry and (not binding or str(binding.get("verified_page_id") or "") != page_id):
                verdict = resolve_page_token({**p, "token_id": token_id}, token_vault, page_manager)
                return jsonify({"success": False, **verdict}), 409
            p["token_id"] = token_id
            if token_entry:
                p["token_name"] = token_entry.get("name", "System User")
                p["page_token"] = binding.get("page_token", "")
                p["mapping_status"] = "VERIFIED"
                p["mapping_verified_at"] = binding.get("verified_at", "")
            else:
                p["token_name"] = "AutoPool (Tự động)"
                p.pop("page_token", None)
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

    # 0. Assign one Page to one verified Token from a selected token group.
    token_group_id = str(data.get("token_group_id") or "").strip()
    auto_verified = data.get("auto_verified") is True
    if token_group_id or auto_verified:
        try:
            max_pages_per_token = int(data.get("max_pages_per_token") or 0)
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Số Page / Token phải là số nguyên"}), 400
        if max_pages_per_token < 0 or max_pages_per_token > 50:
            return jsonify({"success": False, "error": "Số Page / Token phải từ 1 đến 50"}), 400
        token_group = next((g for g in load_token_groups() if str(g.get("id")) == token_group_id), None) if token_group_id else None
        if token_group_id and not token_group:
            return jsonify({"success": False, "error": "Token group not found"}), 404
        sync_errors = []
        if data.get("sync_pages") is True:
            selected_ids = [str(tid) for tid in token_group.get("token_ids", [])] if token_group else [str(t.get("id")) for t in token_vault.list_tokens(mask=False)]
            sync_errors = _sync_group_credentials(selected_ids)
            pages = page_manager.list_pages()
            if token_group:
                token_group["page_ids"] = _group_page_ids(selected_ids, str(token_group.get("page_source_token_id") or ""))
                token_group["pages_synced_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                groups = load_token_groups()
                for group in groups:
                    if str(group.get("id")) == token_group_id:
                        group.update({"page_ids": token_group["page_ids"], "pages_synced_at": token_group["pages_synced_at"]})
                save_token_groups(groups)
        requested = {str(pid) for pid in data.get("page_ids", []) if pid}
        if token_group:
            group_pages = {str(pid) for pid in token_group.get("page_ids", [])}
            if requested - group_pages:
                return jsonify({"success": False, "error": "Page is outside selected Token group snapshot",
                                "blocked": sorted(requested - group_pages)}), 409
            requested = requested or group_pages
        candidates = [p for p in pages if not requested or str(p.get("page_id")) in requested]
        missing = requested - {str(p.get("page_id")) for p in candidates}
        if missing:
            return jsonify({"success": False, "error": "Page not found", "blocked": sorted(missing)}), 404
        if not candidates:
            return jsonify({"success": False, "error": "No Pages in selected Token group"}), 400
        vault_map = {str(t.get("id")): t for t in token_vault.list_tokens(mask=False)}
        token_ids = [str(tid) for tid in token_group.get("token_ids", [])] if token_group else list(vault_map)
        blocked = []
        planned = []
        loads = {tid: 0 for tid in token_ids}
        eligible_ids = {
            tid for tid in token_ids
            if vault_map.get(tid) and vault_map[tid].get("status") == "ACTIVE"
            and any(
                (page.get("token_bindings") or {}).get(tid)
                and (page.get("token_bindings") or {}).get(tid, {}).get("status") == "VERIFIED"
                and (page.get("token_bindings") or {}).get(tid, {}).get("page_token")
                and str((page.get("token_bindings") or {}).get(tid, {}).get("verified_page_id") or "") == str(page.get("page_id"))
                and (page.get("token_bindings") or {}).get(tid, {}).get("credential_fingerprint") == page_manager.credential_fingerprint(vault_map[tid].get("token"))
                for page in candidates
            )
        }
        effective_limit = max_pages_per_token
        if max_pages_per_token and eligible_ids:
            required_limit = (len(candidates) + len(eligible_ids) - 1) // len(eligible_ids)
            # A request such as 3 Page/token with 31 tokens and 100 Pages is
            # intentionally balanced as 3–4 Page/token. Do not reject the
            # remainder when it is only one Page above the requested target.
            if max_pages_per_token >= 3 and len(eligible_ids) >= 2 and required_limit <= max_pages_per_token + 1:
                effective_limit = required_limit
        for page in candidates:
            pid = str(page.get("page_id"))
            choices = []
            for tid in token_ids:
                binding = (page.get("token_bindings") or {}).get(tid)
                credential = vault_map.get(tid)
                if not binding or str(binding.get("verified_page_id") or "") != pid:
                    continue
                if not credential or credential.get("status") != "ACTIVE":
                    continue
                if (binding.get("status") != "VERIFIED" or not binding.get("page_token") or
                        binding.get("credential_fingerprint") != page_manager.credential_fingerprint(credential.get("token"))):
                    continue
                choices.append((tid, binding, credential))
            if not choices:
                blocked.append({"page_id": pid, "code": "missing_mapping"})
                continue
            if effective_limit:
                choices = [choice for choice in choices if loads[choice[0]] < effective_limit]
            if not choices:
                blocked.append({"page_id": pid, "code": "token_capacity"})
                continue
            tid, binding, credential = min(choices, key=lambda choice: (loads[choice[0]], token_ids.index(choice[0])))
            planned.append((page, tid, binding, credential))
            loads[tid] += 1
        if blocked:
            capacity_blocked = any(item["code"] == "token_capacity" for item in blocked)
            minimum_limit = (len(candidates) + len(eligible_ids) - 1) // len(eligible_ids) if eligible_ids else None
            return jsonify({"success": False, "stage": "mapping", "code": "token_capacity" if capacity_blocked else "missing_mapping",
                            "error": (f"Không đủ Token đã xác thực cho giới hạn {max_pages_per_token} Page/Token." if capacity_blocked else "Some selected Pages have no active verified Token mapping in this group. Sync only the blocked Pages with a credential that manages them."),
                            "blocked": blocked, "blocked_count": len(blocked), "eligible_tokens": len(eligible_ids),
                            "selected_pages": len(candidates), "minimum_limit": minimum_limit,
                            "sync_errors": sync_errors, "count": 0}), 409
        for page, tid, binding, credential in planned:
            if data.get("dry_run") is not True:
                page["token_id"] = tid
                page["token_name"] = credential.get("owner_name") or credential.get("name", "System User")
                page["page_token"] = binding["page_token"]
                page["mapping_status"] = "VERIFIED"
                page["mapping_verified_at"] = binding.get("verified_at", "")
        assigned = len(planned)
        if data.get("dry_run") is not True:
            page_manager.save_pages(pages)
            if token_group:
                with _token_group_lock:
                    groups = load_token_groups()
                    current = next(g for g in groups if str(g.get("id")) == token_group_id)
                    assignments = dict(current.get("page_token_bindings") or {})
                    assignments.update({str(page.get("page_id")): tid for page, tid, _binding, _credential in planned})
                    current["page_token_bindings"] = assignments
                    save_token_groups(groups)
        return jsonify({"success": True, "count": assigned, "loads": loads,
                        "requested_limit": max_pages_per_token, "effective_limit": effective_limit,
                        "active_tokens_used": sum(1 for count in loads.values() if count),
                        "dry_run": data.get("dry_run") is True,
                        "over_four": {tid: count for tid, count in loads.items() if count > 4},
                        "sync_errors": sync_errors,
                        "message": f"Assigned {assigned} Pages to verified group Tokens."})

    # 1. Hỗ trợ dạng mảng gán chi tiết từng page (round-robin assignments)
    assignments = data.get("assignments")
    if isinstance(assignments, list) and assignments:
        assign_map = {str(a.get("page_id")): str(a.get("token_id")) for a in assignments if a.get("page_id") and a.get("token_id")}
        vault_map = {str(t.get("id")): t for t in token_vault.list_tokens(mask=False)}
        unknown_ids = sorted({tid for tid in assign_map.values() if tid not in vault_map})
        if unknown_ids:
            return jsonify({"error": "Token không tồn tại trong Vault: " + ", ".join(unknown_ids)}), 404
        blocked = []
        found = {str(p.get("page_id")) for p in pages}
        blocked.extend({"page_id": pid, "code": "missing_page"} for pid in assign_map if pid not in found)
        for p in pages:
            pid = str(p.get("page_id"))
            if pid in assign_map:
                token_id = assign_map[pid]
                token_entry = vault_map[token_id]
                binding = (p.get("token_bindings") or {}).get(token_id)
                if not binding or str(binding.get("verified_page_id") or "") != pid:
                    blocked.append({"page_id": pid, "token_id": token_id, "code": "cross_bound_mapping"})
                    continue
                p["token_id"] = token_id
                p["token_name"] = token_entry.get("name", "System User")
                p["page_token"] = binding.get("page_token", "")
                count += 1
        if blocked:
            return jsonify({
                "success": False,
                "stage": "mapping",
                "code": "cross_bound_mapping",
                "error": "Page/Token mapping is not verified; sync the Page with that token first.",
                "action": "Sync từng Page từ đúng credential; không thể gán token theo vị trí hoặc vòng tròn.",
                "blocked": blocked,
            }), 409
        page_manager.save_pages(pages)
        return jsonify({"success": True, "count": count, "message": f"Đã tự động xoay vòng chia đều token cho {count} trang."})

    # 2. Hỗ trợ dạng gán 1 token_id cho danh sách page_ids
    token_id = str(data.get("token_id", ""))
    page_ids = [str(pid) for pid in data.get("page_ids", [])]
    if not token_id:
        return jsonify({"error": "Thiếu token_id hoặc danh sách phân bổ assignments"}), 400
    token_entry = token_vault.get_token_by_id(token_id)
    if not token_entry:
        return jsonify({"error": "Token không tồn tại trong Vault"}), 404

    for p in pages:
        if str(p.get("page_id")) in page_ids:
            binding = (p.get("token_bindings") or {}).get(token_id)
            if not binding or str(binding.get("verified_page_id") or "") != str(p.get("page_id")):
                return jsonify({
                    "success": False,
                    "stage": "mapping",
                    "code": "cross_bound_mapping",
                    "action": "Token không có mapping được xác minh cho một hoặc nhiều Page đã chọn.",
                }), 409
            p["token_id"] = token_id
            p["token_name"] = token_entry.get("name", "System User")
            p["page_token"] = binding.get("page_token", "")
            count += 1

    page_manager.save_pages(pages)
    return jsonify({"success": True, "count": count, "message": f"Đã gán cứng Token cho {count} trang."})


@app.route("/api/clips/purge_posted", methods=["POST"])
def api_purge_posted_clips():
    """Compatibility endpoint: remove only clips confirmed published."""
    try:
        from web.scheduled_publisher import remove_posted_clip_file
    except ImportError:
        from scheduled_publisher import remove_posted_clip_file
    posts = load_posts()
    deleted_count = 0
    total_freed_bytes = 0
    for clip in sorted({str(p.get("media_file") or p.get("clip_filename") or "").strip() for p in posts}):
        if not clip:
            continue
        candidate = Path(clip)
        if not candidate.is_absolute():
            candidate = OUTPUT_DIR / candidate
        try:
            size = candidate.stat().st_size if candidate.is_file() else 0
        except OSError:
            size = 0
        if remove_posted_clip_file(clip, posts):
            deleted_count += 1
            total_freed_bytes += size
    freed_mb = round(total_freed_bytes / (1024 * 1024), 2)
    return jsonify({"success": True, "deleted_count": deleted_count, "freed_mb": freed_mb,
                    "message": "Da don cac clip da xuat ban va da xac minh."})

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
    youtube_url = data.get("youtube_url", "")
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

    # Ưu tiên YouTube embed để không upload MP4 lên server. Luồng upload cũ chỉ
    # là fallback tương thích cho draft không có nguồn YouTube.
    youtube_id = extract_youtube_video_id(youtube_url)
    public_video_url = ""
    local_video_path = None
    if youtube_url and not youtube_id:
        return jsonify({"success": False, "error": "Link YouTube không hợp lệ"}), 400
    if youtube_id:
        public_video_url = f"https://www.youtube.com/watch?v={youtube_id}"
    elif str(long_video).startswith("https://"):
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
    safe_hook_url = html.escape(hook_img, quote=True) if str(hook_img).startswith("https://") else ""
    if youtube_id:
        video_html = build_youtube_embed_html(youtube_id, title)
    else:
        safe_video_url = html.escape(public_video_url, quote=True)
        video_html = f"""
        <div class="video-container" style="margin: 20px 0; text-align: center;">
          <video controls playsinline preload="metadata" style="width: 100%; max-width: 720px; border-radius: 8px; background: #000;" poster="{safe_hook_url}">
            <source src="{safe_video_url}" type="video/mp4">
            Trình duyệt của bạn không hỗ trợ phát video trực tiếp.
          </video>
        </div>
        """
    body_html = f"""
    <div class="article-content">
      <p class="lead-summary"><strong>{safe_summary}</strong></p>
      {video_html}
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
        first_comment = f"ðŸ”¥ Watch the full uncut footage and breakdown here: {article_url}\nðŸ‘‰ Scroll down the article to stream the complete high-definition video!"

    return jsonify({
        "success": True,
        "article_url": article_url,
        "first_comment": first_comment,
        "hook_image": hook_img,
        "title": title,
        "video_url": public_video_url,
        "cms_verified": not dry_run,
    })


from src.content_packages import (list_packages, get_package, process_content_packages_once,
                                 generate_package, fallback_package, circuit_status,
                                 start_content_package_worker, enqueue_content_package, sanitize_error,
                                 retry_package_component, retry_package, component_statuses,
                                 package_needs_attention, content_worker_settings, content_worker_status)


def apply_ready_package_to_post(post, package):
    """Keep in-memory scheduled entries consistent with a reused persisted package."""
    result = package.get("result") or {}
    from src.english_text import assert_english_package
    assert_english_package(result)
    post["content_package_source"] = result.get("source")
    post["content"] = result.get("caption") or post.get("content", "")
    post["title"] = result.get("hero_title") or post.get("title", "")
    post["article_url"] = package.get("article_url") or post.get("article_url", "")
    post["website_status"] = package.get("website_status", post.get("website_status"))
    post["website_error"] = package.get("website_error", "")
    post["website_embed_status"] = package.get("embed_status") or "unknown"
    if post.get("first_comment_status") != "posted" and not post.get("first_comment_snapshot"):
        post["first_comment"] = result.get("first_comment") or post.get("first_comment", "")
        if post.get("first_comment"):
            post["first_comment_snapshot"] = post["first_comment"]
            post["first_comment_source"] = result.get("first_comment_source") or ("template_fallback" if str(result.get("source") or "").startswith("no_llm") else "")
            post["first_comment_profile_id"] = package.get("first_comment_profile_id") or result.get("first_comment_profile_id") or post.get("first_comment_profile_id", "")
            post["first_comment_profile_name"] = result.get("first_comment_profile_name", "")
            post["first_comment_model"] = result.get("first_comment_model", "")
            post["first_comment_fallback_reason"] = sanitize_error(result.get("first_comment_fallback_reason", ""))
            if post.get("first_comment_status") != "pending":
                post["first_comment_status"] = "ready_after_publish" if post.get("status") in ("published", "processing") else "ready"


def content_studio_article_url(payload):
    url = str(payload.get("article_url") or "").strip()
    if url:
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError()
            parsed.port  # Reject malformed ports as well.
        except ValueError:
            raise ValueError("URL bài viết phải là HTTP(S) hợp lệ, không chứa tài khoản hoặc mật khẩu.") from None
    return url

# ---------------------------------------------------------------------------
# Content Studio: background Content Package queue for rendered clips.
# Schedule creation never blocks here; the queue worker owns LLM/CMS latency.
# ---------------------------------------------------------------------------
@app.route("/api/content-studio/queue", methods=["GET"])
def api_content_studio_queue():
    items = list_packages()
    llm_counts = {"success": 0, "fallback": 0, "pending": 0, "failed": 0, "disabled": 0, "unknown": 0, "blocked_website": 0}
    for item in items:
        item["component_statuses"] = component_statuses(item)
        item["needs_attention"] = package_needs_attention(item)
        source = str((item.get("result") or {}).get("source") or "")
        if source == "llm":
            llm_status = "success"
        elif item.get("mode") == "no_llm":
            llm_status = "disabled"
        elif source.startswith("no_llm"):
            llm_status = "fallback"
        elif item.get("status") in ("queued", "running"):
            llm_status = "pending"
        elif item.get("status") in ("failed", "retryable") and item.get("website_status") == "failed":
            llm_status = "blocked_website"
        elif item.get("status") in ("failed", "retryable"):
            llm_status = "failed"
        else:
            llm_status = "unknown"
        item["llm_status"] = llm_status
        item["llm_error"] = str((item.get("result") or {}).get("fallback_reason") or item.get("error") or "") if llm_status in ("fallback", "failed") else ""
        llm_counts[llm_status] += 1
    return jsonify({
        "success": True,
        "queued": sum(1 for i in items if i.get("status") == "queued"),
        "running": sum(1 for i in items if i.get("status") == "running"),
        "ready": sum(1 for i in items if i.get("status") == "ready"),
        "failed": sum(1 for i in items if i.get("status") == "failed"),
        "retryable": sum(1 for i in items if i.get("status") == "retryable"),
        "needs_attention": sum(1 for i in items if package_needs_attention(i)),
        "items": items,
        "llm_counts": llm_counts,
        "circuit": circuit_status(),
        "worker": content_worker_status(),
    })


@app.route("/api/content-studio/workers", methods=["GET", "PUT"])
def api_content_studio_workers():
    try:
        if request.method == "PUT" and (request.get_json(silent=True) or {}).get("workers") is None:
            return jsonify({"success": False, "error": "Nhập số luồng Content/LLM trước khi lưu."}), 400
        settings = content_worker_settings((request.json or {}).get("workers") if request.method == "PUT" else None)
        if request.method == "PUT":
            start_content_package_worker()
        return jsonify({"success": True, "worker": {**content_worker_status(), **settings}})
    except (TypeError, ValueError) as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@app.route("/api/first-comment-profiles", methods=["GET"])
def api_first_comment_profiles():
    store = load_profile_store(FIRST_COMMENT_PROFILES_FILE)
    if not FIRST_COMMENT_PROFILES_FILE.exists():
        store["profiles"] = builtin_profiles()
    return jsonify({"success": True, **store, "niches": ["police", "sports", "news", "rescue", "reality", "general"]})


@app.route("/api/first-comment-profiles", methods=["POST"])
def api_create_first_comment_profile():
    data = request.json or {}
    store = load_profile_store(FIRST_COMMENT_PROFILES_FILE)
    if not FIRST_COMMENT_PROFILES_FILE.exists():
        store["profiles"] = builtin_profiles()
    data.setdefault("lead_ins", next((p["lead_ins"] for p in store["profiles"] if p.get("niche") == data.get("niche")), store["profiles"][-1]["lead_ins"]))
    try:
        profile = normalize_profile(data)
        if any(item.get("name", "").casefold() == profile["name"].casefold() for item in store["profiles"]):
            return jsonify({"success": False, "error": "Profile name already exists."}), 409
        store["profiles"].append(profile)
        if data.get("make_default") or len(store["profiles"]) == 1:
            store["default_profile_id"] = profile["id"]
        saved = save_profile_store(FIRST_COMMENT_PROFILES_FILE, store)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    return jsonify({"success": True, "profile": profile, **saved}), 201


@app.route("/api/first-comment-profiles/<profile_id>", methods=["PUT", "DELETE"])
def api_update_first_comment_profile(profile_id):
    store = load_profile_store(FIRST_COMMENT_PROFILES_FILE)
    if not FIRST_COMMENT_PROFILES_FILE.exists():
        store["profiles"] = builtin_profiles()
    index = next((i for i, item in enumerate(store["profiles"]) if item.get("id") == profile_id), None)
    if index is None:
        return jsonify({"success": False, "error": "Profile not found."}), 404
    if request.method == "DELETE":
        if len(store["profiles"]) <= 1:
            return jsonify({"success": False, "error": "At least one First Comment profile must remain."}), 409
        del store["profiles"][index]
        if store["default_profile_id"] == profile_id:
            store["default_profile_id"] = store["profiles"][0]["id"]
        saved = save_profile_store(FIRST_COMMENT_PROFILES_FILE, store)
        return jsonify({"success": True, **saved})
    data = request.json or {}
    try:
        profile = normalize_profile(data, profile_id=profile_id)
        if any(i != index and item.get("name", "").casefold() == profile["name"].casefold()
               for i, item in enumerate(store["profiles"])):
            return jsonify({"success": False, "error": "Profile name already exists."}), 409
        store["profiles"][index] = profile
        if data.get("make_default"):
            store["default_profile_id"] = profile_id
        saved = save_profile_store(FIRST_COMMENT_PROFILES_FILE, store)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    return jsonify({"success": True, "profile": profile, **saved})


@app.route("/api/first-comment-profiles/<profile_id>/regenerate", methods=["POST"])
def api_regenerate_first_comment_profile(profile_id):
    store = load_profile_store(FIRST_COMMENT_PROFILES_FILE)
    if not FIRST_COMMENT_PROFILES_FILE.exists():
        store["profiles"] = builtin_profiles()
    profile = next((item for item in store["profiles"] if item.get("id") == profile_id), None)
    if not profile:
        return jsonify({"success": False, "error": "Profile not found."}), 404
    try:
        from src.content_builder import get_llm_candidates, _get_task_model
        from src.llm_response import chat_model_unavailable, json_from_chat_response
        cfg = get_llm_candidates()
        endpoint = str(cfg.get("configured_base") or "").strip()
        model = _get_task_model("first_comment") or cfg.get("model")
        main_model = str(cfg.get("model") or "").strip()
        candidate_models = list(dict.fromkeys(item for item in (model, main_model) if item))
        if not endpoint or not candidate_models or not cfg.get("api_key"):
            return jsonify({"success": False, "error": "Configure a text LLM endpoint, model, and key before generating profile samples."}), 400
        prompt = (
            "Return JSON only as {\"templates\":[30 distinct strings]}. Write short reusable First Comment lead-ins in English only "
            "for niche=" + profile["niche"] + ". Keep every line factual and generic: no named people, event claims, "
            "outcomes, dates, invented details, questions implying an event, or URLs. Each line should invite the reader "
            "to open the article for more context. Lead-in only; the verified article URL is appended later."
        )
        headers = {"Content-Type": "application/json", "Accept": "application/json",
                   "Authorization": f"Bearer {cfg['api_key']}"}
        result = None
        for candidate_model in candidate_models:
            response = requests.post(f"{endpoint.rstrip('/')}/chat/completions", headers=headers,
                                     json={"model": candidate_model, "messages": [{"role": "user", "content": prompt}],
                                           "max_tokens": 1800, "temperature": 0.65}, timeout=45)
            if response.status_code != 200:
                raise RuntimeError(f"Text LLM returned HTTP {response.status_code}.")
            if chat_model_unavailable(response):
                continue
            result = json_from_chat_response(response)
            break
        if result is None:
            raise RuntimeError("Configured First Comment model is unavailable; choose an active text model or repair the task model setting.")
        samples = result.get("templates") if isinstance(result, dict) else None
        from src.first_comment_profiles import _valid_lead_ins
        samples = _valid_lead_ins(samples, minimum=30)
        profile = normalize_profile({**profile, "lead_ins": samples}, profile_id=profile_id)
        store["profiles"] = [profile if item.get("id") == profile_id else item for item in store["profiles"]]
        saved = save_profile_store(FIRST_COMMENT_PROFILES_FILE, store)
    except (ValueError, RuntimeError) as exc:
        return jsonify({"success": False, "error": sanitize_error(exc)}), 502
    except Exception as exc:
        return jsonify({"success": False, "error": sanitize_error(exc) if isinstance(exc, (ValueError, RuntimeError)) else type(exc).__name__}), 502
    return jsonify({"success": True, "profile": profile, **saved})

@app.route("/api/content-studio/generate", methods=["POST"])
def api_content_studio_generate():
    payload = request.json or {}
    clip = str(payload.get("clip_filename") or payload.get("filename") or "").strip()
    title = str(payload.get("title") or "").strip()
    if not title and clip:
        meta = get_clip_metadata(clip)
        title = str(meta.get("video_title") or meta.get("clean_title") or "").strip()
    if not title:
        return jsonify({"success": False, "error": "Thiếu tiêu đề hoặc clip để tạo nội dung"}), 400
    mode = str(payload.get("mode") or "auto")
    if mode not in ("auto", "llm", "no_llm"):
        return jsonify({"success": False, "error": "mode phải là auto, llm hoặc no_llm"}), 400
    component = str(payload.get("component") or "").strip()
    try:
        article_url = content_studio_article_url(payload)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    try:
        result = generate_package(
            title,
            str(payload.get("summary") or ""),
            str(payload.get("video_url") or ""),
            mode=mode,
            article_url=article_url,
            component=component,
            profile_id=str(payload.get("first_comment_profile_id") or ""),
            niche=str(payload.get("niche") or "").strip(),
            fallback_strategy=str(payload.get("fallback_strategy") or "rotate"),
        )
    except Exception as exc:
        return jsonify({"success": False, "error": sanitize_error(exc)}), 502
    return jsonify({"success": True, "mode": mode, "component": component or "all", "package": result})

@app.route("/api/content-studio/enqueue", methods=["POST"])
def api_content_studio_enqueue():
    payload = request.json or {}
    clip = str(payload.get("clip_filename") or payload.get("filename") or "").strip()
    title = str(payload.get("title") or "").strip()
    if not clip and not title:
        return jsonify({"success": False, "error": "Cần clip_filename hoặc title để xếp hàng"}), 400
    try:
        article_url = content_studio_article_url(payload)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    item = enqueue_content_package(
        clip_filename=clip,
        title=title or clip,
        summary=str(payload.get("summary") or ""),
        video_url=str(payload.get("video_url") or ""),
        mode=str(payload.get("mode") or "auto"),
        post_ids=list(payload.get("post_ids") or []),
        article_url=article_url,
        create_website_article=bool(payload.get("create_website_article")) and not article_url,
        first_comment_profile_id=str(payload.get("first_comment_profile_id") or ""),
        niche=str(payload.get("niche") or "").strip(),
        fallback_strategy=str(payload.get("fallback_strategy") or "rotate"),
    )
    start_content_package_worker()
    return jsonify({"success": True, "item": item})

@app.route("/api/content-studio/batch", methods=["POST"])
def api_content_studio_batch():
    payload = request.json or {}
    folder = str(payload.get("folder") or payload.get("directory") or "").strip()
    if not folder:
        return jsonify({"success": False, "error": "Vui lòng nhập đường dẫn thư mục clip."}), 400
    folder_path = Path(folder).expanduser()
    if not folder_path.is_dir():
        return jsonify({"success": False, "error": f"Không tìm thấy thư mục: {folder}"}), 404
    extensions = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
    clips = sorted((p for p in folder_path.iterdir() if p.is_file() and p.suffix.lower() in extensions), key=lambda p: p.name.lower())
    if not clips:
        return jsonify({"success": False, "error": "Thư mục không có file video hỗ trợ."}), 400
    mode = str(payload.get("mode") or "auto")
    if mode not in ("auto", "llm", "no_llm"):
        return jsonify({"success": False, "error": "mode phải là auto, llm hoặc no_llm"}), 400
    # A clip is already handled when it is in posted_clips.json or already has
    # a package in the persisted queue. Compare normalized absolute paths and
    # basenames so old records created with a different folder prefix do not
    # get re-enqueued.
    def _clip_keys(value):
        raw = str(value or "").strip()
        if not raw:
            return set()
        path = Path(raw)
        return {raw.lower(), path.name.lower()}

    posted_file = POSTS_FILE.parent / "posted_clips.json"
    posted_records = []
    if posted_file.exists():
        try:
            posted_records = json.loads(posted_file.read_text(encoding="utf-8"))
        except Exception:
            posted_records = []
    posted_keys = set()
    for record in posted_records if isinstance(posted_records, list) else []:
        if isinstance(record, dict):
            for field in ("clip_filename", "media_file", "filename", "path"):
                posted_keys.update(_clip_keys(record.get(field)))
        else:
            posted_keys.update(_clip_keys(record))
    # The legacy clip ledger can lag behind a confirmed posts.json revision.
    # A published post with a Meta object id is stronger evidence than an
    # absent ledger row; neither scheduled nor ambiguous posts are "posted".
    for post in load_posts():
        if post.get("status") == "published" and (post.get("post_fb_id") or post.get("reel_id")):
            posted_keys.update(_clip_keys(post.get("media_file") or post.get("clip_filename")))
    existing_keys = set()
    for item in list_packages():
        if str(item.get("status") or "") in ("queued", "running", "ready", "retryable"):
            existing_keys.update(_clip_keys(item.get("clip_filename")))

    created = []
    skipped = []
    for clip_path in clips:
        keys = _clip_keys(clip_path) | _clip_keys(str(clip_path))
        if keys & posted_keys:
            skipped.append({"clip": str(clip_path), "reason": "already_posted"})
            continue
        if keys & existing_keys:
            skipped.append({"clip": str(clip_path), "reason": "already_in_content_queue"})
            continue
        title = clip_path.stem.replace("_", " ").strip()
        try:
            meta = get_clip_metadata(str(clip_path)) or {}
            title = str(meta.get("video_title") or meta.get("clean_title") or title).strip()
        except Exception:
            pass
        created_item = enqueue_content_package(
            clip_filename=str(clip_path), title=title, mode=mode,
            create_website_article=bool(payload.get("create_website_article")),
            first_comment_profile_id=str(payload.get("first_comment_profile_id") or ""),
            niche=str(payload.get("niche") or "").strip(),
            fallback_strategy=str(payload.get("fallback_strategy") or "rotate"),
        )
        created.append(created_item)
        existing_keys.update(keys)
    if created:
        start_content_package_worker()
    return jsonify({"success": True, "folder": str(folder_path), "count": len(created), "skipped_count": len(skipped), "skipped": skipped, "items": created})

@app.route("/api/content-studio/retry", methods=["POST"])
def api_content_studio_retry():
    payload = request.json or {}
    package_id = str(payload.get("id") or "").strip()
    item = get_package(package_id) if package_id else None
    if not item:
        return jsonify({"success": False, "error": "Không tìm thấy Content Package"}), 404
    component = str(payload.get("component") or "").strip()
    try:
        if component:
            result = retry_package_component(package_id, component, str(payload.get("mode") or item.get("mode") or "auto"))
            if not result:
                return jsonify({"success": False, "error": "Không tìm thấy Content Package"}), 404
            return jsonify({"success": True, **result})
        mode = str(payload.get("mode") or "").strip()
        if mode and mode not in ("auto", "llm", "no_llm"):
            return jsonify({"success": False, "error": "mode phải là auto, llm hoặc no_llm"}), 400
        queued = retry_package(package_id, mode=mode or None)
        if not queued:
            return jsonify({"success": False, "error": "Không tìm thấy Content Package"}), 404
        if queued.get("status") != "queued":
            return jsonify({"success": False, "error": "Chỉ có thể thử lại mục lỗi hoặc cần retry", "item": queued}), 409
        start_content_package_worker()
        return jsonify({"success": True, "queued": True, "item": queued})
    except Exception as exc:
        return jsonify({"success": False, "error": sanitize_error(exc)}), 502
    return jsonify({"success": True, "component": component or "all", "package": result})

@app.route("/api/content-studio/fallback", methods=["GET"])
def api_content_studio_fallback():
    title = str(request.args.get("title") or "Untold Highlight")
    return jsonify({
        "success": True,
        "package": fallback_package(title, str(request.args.get("summary") or ""), str(request.args.get("article_url") or "")),
        "circuit": circuit_status(),
    })

@app.route("/api/content-studio/process", methods=["POST"])
def api_content_studio_process():
    start_content_package_worker()
    return jsonify({"success": True, "queued": True, "worker": content_worker_status(),
                    "message": "Hàng đợi tự xử lý các clip đang chờ; theo dõi video và từng bước tại Content Studio."}), 202


if __name__ == "__main__":
    import waitress
    bind_host = os.environ.get("HIGHLIGHT_BIND_HOST", "127.0.0.1").strip() or "127.0.0.1"
    print(f"Highlight Video Studio starting on http://{bind_host}:5080 with Waitress (threads=8)...")
    waitress.serve(app, host=bind_host, port=5080, threads=8, channel_timeout=30)

