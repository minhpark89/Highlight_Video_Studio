from pathlib import Path

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

old_part = """        # Link website bài viết chi tiết để kích thích tò mò
        article_url = f"https://bestnews.cfx.bz/article/{slug}"
        first_comm = f"🔥 Xem trọn vẹn bản full diễn biến tình huống tại: {article_url}\\n👉 Kéo xuống bài viết để xem trọn bộ video dài không cắt!"

        post_entry = {
            "id": post_id,
            "title": f"{clean_title.title()}",
            "content": f"Xem ngay diễn biến kịch tính nhất! Chi tiết trọn bộ bài viết và video dài tại website.\\n#reels #viral #highlight",
            "hashtags": "#reels #trending #highlight #viral","""

new_part = """        # Link website bài viết chi tiết để kích thích tò mò (FULL TIẾNG ANH CHUẨN QUỐC TẾ)
        article_url = f"https://bestnews.cfx.bz/article/{slug}"
        first_comm = f"🔥 Watch the full uncut footage and breakdown here: {article_url}\\n👉 Scroll down the article to stream the complete high-definition video!"

        post_entry = {
            "id": post_id,
            "title": f"{clean_title.title()}",
            "content": f"Watch the thrilling highlights & full breakdown! Check the official footage link in the first comment below.\\n#reels #trending #highlight #viral #sports",
            "hashtags": "#reels #trending #highlight #viral #sports","""

if old_part in text:
    text = text.replace(old_part, new_part)
    app_path.write_text(text, encoding="utf-8")
    print("Updated First Comment and Content to English successfully!")
else:
    print("Could not find exact old_part")
