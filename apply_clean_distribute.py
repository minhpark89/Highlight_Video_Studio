import json
from pathlib import Path

app_py_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
content = app_py_path.read_text(encoding="utf-8")

pos_start = content.find('@app.route("/api/distribute/batch", methods=["POST"])')
pos_next_route = content.find('@app.route("/api/schedule/rules"', pos_start)

print("Target span:", pos_start, pos_next_route)

# Write pure clean python code into target
new_code = '''@app.route("/api/distribute/batch", methods=["POST"])
def api_distribute_batch():
    import re
    from datetime import datetime, timedelta
    data = request.json or {}
    group_id = data.get("group_id")
    clip_filenames = data.get("clip_filenames", [])
    posts_per_page = int(data.get("posts_per_page", 1))
    stagger_minutes = int(data.get("stagger_minutes", 15))
    auto_first_comment = data.get("auto_first_comment", True)

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
    available_tokens = token_vault.list_tokens()
    posts = load_posts()

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
            page_token = p_info.get("access_token", "")
            if not page_token and available_tokens:
                tok_obj = available_tokens[idx % len(available_tokens)]
                page_token = tok_obj.get("token", "")

            post_id = f"post_{int(time.time())}_{uuid.uuid4().hex[:6]}"
            sched_dt = slot_base_dt + timedelta(minutes=(idx * group_stagger))
            sched_time_str = sched_dt.strftime("%Y-%m-%d %H:%M:%S")

            raw_name = Path(clip_fn).stem
            clean_title = re.sub(r'^(job_\\d+_[a-f0-9]+_|clip_\\d+_)', '', raw_name, flags=re.IGNORECASE)
            clean_title = clean_title.replace('_', ' ').strip()
            if not clean_title:
                clean_title = f"Highlight Moments #{scheduled_count+1}"

            slug = f"clip-{int(time.time())}-{uuid.uuid4().hex[:4]}"
            article_url = f"https://bestnews.cfx.bz/article/{slug}"
            first_comm = f"🔥 Watch the full uncut footage and breakdown here: {article_url}\\n👉 Scroll down the article to stream the complete high-definition video!"

            post_entry = {
                "id": post_id,
                "title": f"{clean_title.title()}",
                "content": f"Watch the thrilling highlights & full breakdown! Check the official footage link in the first comment below.\\n#reels #trending #highlight #viral #sports",
                "hashtags": "#reels #trending #highlight #viral #sports",
                "page_id": pid,
                "page_name": p_info.get("page_name", f"Fanpage {pid}"),
                "group_id": group_id,
                "group_name": group.get("name", "Nhóm Fanpage"),
                "type": "reel",
                "media_file": clip_fn,
                "first_comment": first_comm if auto_first_comment else "",
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

'''

content = content[:pos_start] + new_code + content[pos_next_route:]
app_py_path.write_text(content, encoding="utf-8")
print("Successfully updated app.py!")
