import threading
import time
from datetime import datetime
from pathlib import Path
import json

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
POSTS_FILE = BASE_DIR / "posts.json"
POSTED_CLIPS_FILE = BASE_DIR / "posted_clips.json"
OUTPUT_DIR = BASE_DIR / "output"

_FILE_LOCK = threading.Lock()

def load_posts():
    with _FILE_LOCK:
        if not POSTS_FILE.exists():
            return []
        try:
            return json.loads(POSTS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []

def save_posts(posts):
    with _FILE_LOCK:
        POSTS_FILE.write_text(json.dumps(posts, indent=2, ensure_ascii=False), encoding="utf-8")

def scheduled_publisher_worker_loop():
    """
    Background worker loop chạy định kỳ mỗi 20 giây:
    Được thiết kế an toàn chống Double-post (Idempotency & Claim lock):
    1. Khi tìm thấy bài due (status == 'scheduled' và scheduled_time <= now):
       Lập tức CLAIM bài đó thành 'publishing' và ghi file posts.json ngay.
    2. Nếu restart giữa chừng: các bài 'publishing' được bảo vệ, tránh gọi trùng Meta Graph API.
    3. Chỉ khi nào Meta Graph API trả về thành công có video_id thì mới chuyển sang 'published' và ghi posted_clips.json.
    """
    import sys
    sys.path.insert(0, str(BASE_DIR))
    from src.publisher.meta_reel_poster import MetaReelPoster

    poster = MetaReelPoster()
    print("[ScheduledPublisher] Background publisher worker started with Idempotent Claim Lock!")

    while True:
        try:
            posts = load_posts()
            now = datetime.now()

            # BƯỚC 1: TÌM & CLAIM CÁC BÀI ĐẾN GIỜ (ATOMIC CLAIM TRÁNH DOUBLE POST)
            claimed_posts = []
            for p in posts:
                if p.get("status") == "scheduled":
                    sched_time_str = p.get("scheduled_time")
                    if not sched_time_str:
                        continue
                    try:
                        sched_dt = datetime.strptime(sched_time_str[:19], "%Y-%m-%d %H:%M:%S")
                    except Exception:
                        continue

                    if sched_dt <= now:
                        p["status"] = "publishing"
                        p["claimed_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
                        claimed_posts.append(p)

            if claimed_posts:
                save_posts(posts)
                print(f"[ScheduledPublisher] Claimed {len(claimed_posts)} due posts for publishing.")

            # BƯỚC 2: TIẾN HÀNH ĐĂNG TỪNG BÀI ĐÃ CLAIM
            if claimed_posts:
                for p in claimed_posts:
                    p_id = p.get("id")
                    page_id = p.get("page_id")
                    page_name = p.get("page_name")
                    clip_fn = p.get("media_file") or p.get("clip_filename")
                    token = p.get("token")
                    title = p.get("title", "")
                    content = p.get("content", "")
                    first_comment = p.get("first_comment", "")

                    video_path = OUTPUT_DIR / clip_fn if clip_fn else None
                    if not video_path or not video_path.exists():
                        p["status"] = "failed"
                        p["error"] = f"Không tìm thấy file video: {clip_fn}"
                        continue

                    print(f"[ScheduledPublisher] 🚀 Publishing Reel to {page_name} ({page_id})...")
                    try:
                        res = poster.publish_reel(
                            page_id=page_id,
                            page_token=token,
                            video_path=str(video_path),
                            description=f"{title}\n\n{content}",
                            first_comment=first_comment
                        )

                        if res.get("success"):
                            p["status"] = "published"
                            p["post_fb_id"] = res.get("video_id") or res.get("reel_id")
                            p["comment_id"] = res.get("comment_result", {}).get("comment_id")
                            p["published_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(f"[ScheduledPublisher] ✅ Published successfully: {p_id} -> Reel ID: {p['post_fb_id']}")

                            try:
                                with _FILE_LOCK:
                                    posted_list = []
                                    if POSTED_CLIPS_FILE.exists():
                                        posted_list = json.loads(POSTED_CLIPS_FILE.read_text(encoding="utf-8"))
                                    if clip_fn not in posted_list:
                                        posted_list.append(clip_fn)
                                        POSTED_CLIPS_FILE.write_text(json.dumps(posted_list, indent=2), encoding="utf-8")
                            except Exception as ep:
                                print("[ScheduledPublisher] Error saving posted_clips:", ep)
                        else:
                            p["status"] = "failed"
                            p["error"] = res.get("error", "Lỗi Meta Graph API không xác định")
                            print(f"[ScheduledPublisher] ❌ Publish failed for {p_id}: {p['error']}")

                    except Exception as e_pub:
                        p["status"] = "failed"
                        p["error"] = str(e_pub)
                        print(f"[ScheduledPublisher] ❌ Exception during publish {p_id}: {e_pub}")

                save_posts(posts)

        except Exception as e_loop:
            print(f"[ScheduledPublisher] Loop Error: {e_loop}")

        time.sleep(20)
