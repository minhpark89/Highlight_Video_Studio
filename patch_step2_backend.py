import os, json, re, shutil
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
APP_FILE = BASE_DIR / "web" / "app.py"

print("[2/4] Patching app.py...")
with open(APP_FILE, "r", encoding="utf-8") as f:
    code = f.read()

shutil.copy2(APP_FILE, APP_FILE.with_suffix(".py.bak_loha_clean"))

# 1. Thêm import và service kết nối bài viết website
import_snippet = """import sys
from pathlib import Path
NVS_DIR = Path(r"D:\\News_Video_Studio")
if str(NVS_DIR) not in sys.path:
    sys.path.append(str(NVS_DIR))
try:
    from core.website_article_service import WebsiteArticleService
    HAS_WEBSITE_SVC = True
except Exception as _e:
    HAS_WEBSITE_SVC = False
"""

if "HAS_WEBSITE_SVC" not in code:
    code = import_snippet + "\n" + code

# 2. Bổ sung API dọn dẹp các clip đã đăng hoặc đã phân bổ để giải phóng ổ D
clean_api_snippet = """
@app.route("/api/clips/purge_posted", methods=["POST"])
def api_purge_posted_clips():
    \"\"\"
    Xóa tất cả các video clip đã được đánh dấu 'is_posted' hoặc đã đưa vào lịch thành công
    giúp giải phóng dung lượng ổ D và chống đăng trùng video.
    \"\"\"
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
    \"\"\"
    Tạo bài viết web kèm video dài trực tiếp (không link ngoài) và ảnh hook gây tò mò.
    Sinh link chính thức để đưa vào First Comment kéo traffic về web.
    \"\"\"
    data = request.json or {}
    title = data.get("title", "").strip()
    summary = data.get("summary", "").strip()
    hook_img = data.get("hook_image", "") # đường dẫn hoặc URL ảnh hook
    long_video = data.get("video_path", "")
    dry_run = data.get("dry_run", False)

    if not title:
        return jsonify({"success": False, "error": "Thiếu tiêu đề bài viết"}), 400

    cfg_file = NVS_DIR / "data" / "registry" / "website_config.json"
    if not cfg_file.exists():
        cfg_file = BASE_DIR / "config" / "website_config.json"

    article_url = ""
    hook_caption = ""
    
    # Tạo nội dung HTML nhúng video dài chuẩn (thẻ <video> nội bộ hoặc direct stream, không gắn link youtube)
    body_html = f\"\"\"
    <div class="article-content">
      <p class="lead-summary"><strong>{summary or title}</strong></p>
      <div class="video-container" style="margin: 20px 0; text-align: center;">
        <video controls style="width: 100%; max-width: 720px; border-radius: 8px;" poster="{hook_img}">
          <source src="{long_video}" type="video/mp4">
          Trình duyệt của bạn không hỗ trợ phát video trực tiếp.
        </video>
      </div>
      <p>Xem toàn bộ diễn biến chi tiết và cập nhật mới nhất ở trên.</p>
    </div>
    \"\"\"

    slug = re.sub(r'[^a-zA-Z0-9]+', '-', title.lower()).strip('-')[:60]
    
    if HAS_WEBSITE_SVC and cfg_file.exists():
        try:
            svc = WebsiteArticleService(str(cfg_file))
            res = svc.publish_article(
                title=title,
                slug=slug,
                body_html=body_html,
                image_path=hook_img if os.path.exists(hook_img) else None,
                dry_run=dry_run
            )
            article_url = res.get("article_url", f"https://bestnews.cfx.bz/blog/{slug}")
        except Exception as e:
            print("[WebsiteService Error]", e)
            article_url = f"https://bestnews.cfx.bz/blog/{slug}"
    else:
        article_url = f"https://bestnews.cfx.bz/blog/{slug}"

    # First comment kích thích tò mò có kèm ảnh hook & link web
    first_comment = f"🔥 Xem trọn vẹn video bản full dài và chi tiết tình huống tại: {article_url}\\n(Ảnh trích xuất khoảnh khắc gây chú ý nhất bên dưới 👇)"

    return jsonify({
        "success": True,
        "article_url": article_url,
        "first_comment": first_comment,
        "hook_image": hook_img,
        "title": title
    })
"""

# Chèn snippet vào trước main
if "api_purge_posted_clips" not in code:
    main_idx = code.rfind("if __name__ ==")
    if main_idx != -1:
        code = code[:main_idx] + clean_api_snippet + "\n\n" + code[main_idx:]
    else:
        code += "\n\n" + clean_api_snippet

# 3. Cập nhật api_distribute_batch để đảm bảo: 1 VIDEO -> 1 PAGE DUY NHẤT (không trùng lặp, chia đều)
# và tự đánh dấu clip đã lên lịch vào posted_clips.json
old_dist_start = code.find("def api_distribute_batch():")
if old_dist_start != -1:
    old_dist_end = code.find("\nDATA_DIR =", old_dist_start)
    if old_dist_end == -1:
        old_dist_end = code.find("\n@app.route", old_dist_start + 30)

    new_dist_code = """def api_distribute_batch():
    \"\"\"
    Quy trình LoHa Page chuẩn: 1 VIDEO CHO ĐÚNG 1 FANPAGE (Tránh trùng lặp, dọn gọn ổ D)
    Lấy danh sách clip unposted, chia 1:1 cho từng Fanpage trong nhóm, lên lịch kèm First Comment.
    \"\"\"
    data = request.json or {}
    group_id = data.get("group_id")
    clip_filenames = data.get("clip_filenames", [])
    start_time = data.get("start_time") # "YYYY-MM-DDTHH:MM"
    stagger_minutes = int(data.get("stagger_minutes", 15))
    auto_first_comment = data.get("auto_first_comment", True)
    delete_after_schedule = data.get("delete_after_schedule", False)

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
    posts = load_posts()

    # Base schedule time
    if start_time:
        try:
            s_clean = start_time.replace("T", " ")
            if len(s_clean) == 16:
                s_clean += ":00"
            base_dt = datetime.strptime(s_clean[:19], "%Y-%m-%d %H:%M:%S")
        except Exception:
            base_dt = datetime.now() + timedelta(minutes=20)
    else:
        base_dt = datetime.now() + timedelta(minutes=20)

    # Đọc danh sách clip đã post để LOẠI TRỪ TUYỆT ĐỐI không chia trùng
    posted_file = BASE_DIR / "posted_clips.json"
    posted_set = set()
    if posted_file.exists():
        try:
            posted_set = set(json.loads(posted_file.read_text(encoding="utf-8")))
        except Exception:
            posted_set = set()

    # Lọc lấy các clip khả dụng
    available_clips = []
    if clip_filenames:
        for fn in clip_filenames:
            if fn not in posted_set and (OUTPUT_DIR / fn).exists():
                available_clips.append(fn)
    else:
        # Tự động quét kho clips unposted
        for p in OUTPUT_DIR.glob("*.mp4"):
            if p.name not in posted_set:
                available_clips.append(p.name)

    if not available_clips:
        return jsonify({"error": "Không còn video clip mới nào chưa đăng để phân bổ! Hãy render thêm hoặc bỏ lọc."}), 400

    scheduled_count = 0
    assigned_clips = []

    # QUY TẮC: 1 VIDEO CHO 1 PAGE (1:1)
    # Lặp qua từng page, mỗi page lấy đúng 1 video độc nhất từ kho clip khả dụng
    for i, pid in enumerate(page_ids):
        if i >= len(available_clips):
            break # Hết video khả dụng cho các page sau, dừng lại an toàn

        p_info = next((p for p in pages if p.get("page_id") == pid), None)
        if not p_info:
            continue

        clip_fn = available_clips[i]
        clip_path = OUTPUT_DIR / clip_fn

        # Tính thời gian hẹn giờ giãn cách (stagger) tránh dính spam FB
        sched_dt = base_dt + timedelta(minutes=i * stagger_minutes)
        sched_time_str = sched_dt.strftime("%Y-%m-%d %H:%M:%S")
        post_id = f"post_{int(time.time())}_{uuid.uuid4().hex[:6]}"

        clean_title = clip_fn.rsplit('.', 1)[0].replace('_', ' ')
        slug = re.sub(r'[^a-zA-Z0-9]+', '-', clean_title.lower()).strip('-')[:50]
        
        # Link website bài viết chi tiết để kích thích tò mò
        article_url = f"https://bestnews.cfx.bz/article/{slug}"
        first_comm = f"🔥 Xem trọn vẹn bản full diễn biến tình huống tại: {article_url}\\n👉 Kéo xuống bài viết để xem trọn bộ video dài không cắt!"

        post_entry = {
            "id": post_id,
            "title": f"{clean_title.title()}",
            "content": f"Xem ngay diễn biến kịch tính nhất! Chi tiết trọn bộ bài viết và video dài tại website.\\n#reels #viral #highlight",
            "hashtags": "#reels #trending #highlight #viral",
            "page_id": pid,
            "page_name": p_info.get("page_name", f"Fanpage {pid}"),
            "group_id": group_id,
            "group_name": group.get("name", "Nhóm Fanpage"),
            "type": "reel",
            "media_file": clip_fn,
            "first_comment": first_comm if auto_first_comment else "",
            "status": "scheduled",
            "scheduled_time": sched_time_str,
            "posted_at": "",
            "url": "",
            "token_name": p_info.get("token_name") or "System User",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "error_msg": ""
        }
        posts.insert(0, post_entry)
        scheduled_count += 1
        assigned_clips.append(clip_fn)
        posted_set.add(clip_fn)

    # Lưu posts mới vào database
    save_posts(posts)

    # Đánh dấu các clip này vào posted_clips.json để không bao giờ phân bổ trùng lặp
    try:
        with open(posted_file, "w", encoding="utf-8") as pf:
            json.dump(list(posted_set), pf, ensure_ascii=False, indent=2)
    except Exception as ex:
        print("[Error saving posted_clips]", ex)

    # Tùy chọn: Xóa ngay file trên ổ D nếu bật delete_after_schedule (hoặc giữ lại đến khi hoàn tất đăng)
    freed_mb = 0
    if delete_after_schedule:
        for fn in assigned_clips:
            fp = OUTPUT_DIR / fn
            if fp.exists():
                try:
                    freed_mb += round(fp.stat().st_size / (1024 * 1024), 2)
                    fp.unlink()
                except Exception:
                    pass

    return jsonify({
        "success": True, 
        "scheduled_count": scheduled_count, 
        "group_name": group.get("name"),
        "total_pages": len(page_ids),
        "assigned_clips": assigned_clips,
        "freed_mb": freed_mb,
        "message": f"Đã phân bổ thành công {scheduled_count} video độc nhất (1 video : 1 page) cho nhóm '{group.get('name')}'"
    })"""
    
    code = code[:old_dist_start] + new_dist_code + code[old_dist_end:]
    print("Replaced api_distribute_batch with 1-video-1-page logic successfully!")

with open(APP_FILE, "w", encoding="utf-8") as f:
    f.write(code)

print("[2/4] app.py updated successfully!")
