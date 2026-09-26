from pathlib import Path

app_text = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")

old_snippet = """        # Sinh link bài viết kích thích tò mò
        article_url = f"https://bestnews.cfx.bz/article/{slug}"
        first_comm = f"🔥 Xem trọn vẹn bản full diễn biến tình huống tại: {article_url}\\n👉 Kéo xuống bài viết để xem trọn bộ video dài không cắt!"

        post_entry = {
            "id": post_id,
            "title": f"{clean_title.title()}",
            "content": f"Xem ngay diễn biến kịch tính nhất! Chi tiết trọn bộ bài viết tại {article_url}",
            "hashtags": "#highlights #football #viral #video",
            "page_id": page_id,
            "page_name": page_name,
            "group_id": group_id,
            "group_name": group.get("name", ""),
            "clip_filename": clip_fn,
            "video_url": f"/api/clips/play/{clip_fn}",
            "token": page_token,
            "first_comment": first_comm,
            "status": "scheduled",
            "scheduled_time": sched_time_str,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }"""

new_snippet = """        # Sinh link bài viết kích thích tò mò FULL TIẾNG ANH CHUẨN QUỐC TẾ
        article_url = f"https://bestnews.cfx.bz/article/{slug}"
        first_comm = f"🔥 Watch the full uncut footage and breakdown here: {article_url}\\n👉 Scroll down the article to stream the complete high-definition video!"

        post_entry = {
            "id": post_id,
            "title": f"{clean_title.title()}",
            "content": f"Watch the thrilling highlights & full breakdown! Check the official footage link in the first comment below.",
            "hashtags": "#highlights #sports #trending #viral #reels",
            "page_id": page_id,
            "page_name": page_name,
            "group_id": group_id,
            "group_name": group.get("name", ""),
            "clip_filename": clip_fn,
            "video_url": f"/api/clips/play/{clip_fn}",
            "token": page_token,
            "first_comment": first_comm,
            "status": "scheduled",
            "scheduled_time": sched_time_str,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }"""

if old_snippet in app_text:
    app_text = app_text.replace(old_snippet, new_snippet)
    Path(r"D:\Highlight_Video_Studio\web\app.py").write_text(app_text, encoding="utf-8")
    print("Updated First Comment and Post Content to FULL ENGLISH!")
else:
    print("Could not find exact old_snippet in app.py")
