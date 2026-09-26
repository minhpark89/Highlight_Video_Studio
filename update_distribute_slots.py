from pathlib import Path

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

old_distribute = """    # QUY TẮC: 1 VIDEO DUY NHẤT CHO 1 FANPAGE DUY NHẤT (LoHa standard)
    now_ts = datetime.now()
    clip_idx = 0

    for idx, pid in enumerate(page_ids):
        if clip_idx >= len(available_clips):
            break

        clip_fn = available_clips[clip_idx]
        clip_idx += 1

        p_info = page_map.get(pid, {})
        page_token = p_info.get("access_token", "")
        # Tự động gán token xoay vòng nếu page chưa có token
        if not page_token and available_tokens:
            tok_obj = available_tokens[idx % len(available_tokens)]
            page_token = tok_obj.get("token", "")

        post_id = f"post_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        sched_dt = base_dt + timedelta(minutes=(idx * stagger_minutes))
        sched_time_str = sched_dt.strftime("%Y-%m-%d %H:%M:%S")

        raw_name = Path(clip_fn).stem
        clean_title = re.sub(r'^(job_\d+_[a-f0-9]+_|clip_\d+_)', '', raw_name, flags=re.IGNORECASE)
        clean_title = clean_title.replace('_', ' ').strip()
        if not clean_title:
            clean_title = f"Highlight Moments #{idx+1}"

        slug = f"clip-{int(time.time())}-{uuid.uuid4().hex[:4]}"

        # Link website bài viết chi tiết để kích thích tò mò (FULL TIẾNG ANH CHUẨN QUỐC TẾ)
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
        }"""

new_distribute = """    # QUY TẮC LOHAPAGE: HỖ TRỢ posts_per_page (1, 2, HOẶC 4 BÀI / TRANG / NGÀY)
    # Rải đều vào các khung giờ đã cấu hình của nhóm: e.g. ["07:00", "11:30", "17:00", "20:00"]
    posts_per_page = int(data.get("posts_per_page", 1))
    sched_cfg = group.get("schedule_config") or {}
    group_times = sched_cfg.get("times") or ["07:00", "11:30", "17:00", "20:00"]

    now_ts = datetime.now()
    clip_idx = 0

    for slot_idx in range(posts_per_page):
        # Lấy khung giờ tương ứng cho đợt post này
        time_str = group_times[slot_idx % len(group_times)] if group_times else "11:30"
        try:
            th, tm = map(int, time_str.split(":"))
        except Exception:
            th, tm = 11, 30

        # Xác định ngày post (hôm nay hoặc ngày mai nếu giờ đã qua)
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
            # Giãn cách stagger giữa các page
            sched_dt = slot_base_dt + timedelta(minutes=(idx * stagger_minutes))
            sched_time_str = sched_dt.strftime("%Y-%m-%d %H:%M:%S")

            raw_name = Path(clip_fn).stem
            clean_title = re.sub(r'^(job_\\d+_[a-f0-9]+_|clip_\\d+_)', '', raw_name, flags=re.IGNORECASE)
            clean_title = clean_title.replace('_', ' ').strip()
            if not clean_title:
                clean_title = f"Highlight Moments #{idx+1}"

            slug = f"clip-{int(time.time())}-{uuid.uuid4().hex[:4]}"

            # Link website bài viết chi tiết để kích thích tò mò (FULL TIẾNG ANH CHUẨN QUỐC TẾ)
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
            }"""

if old_distribute in app_text:
    app_text = app_text.replace(old_distribute, new_distribute)
    Path(r"D:\Highlight_Video_Studio\web\app.py").write_text(app_text, encoding="utf-8")
    print("Updated api_distribute_batch to support multi-slot posts_per_page & group_times!")
else:
    print("Could not find exact old_distribute in app.py")
