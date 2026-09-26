from pathlib import Path

txt = Path(r"D:\Highlight_Video_Studio\web\scheduled_publisher.py").read_text(encoding="utf-8")

old_call = """                        # Call MetaReelPoster
                        try:
                            res = poster.publish_reel(
                                page_id=page_id,
                                page_access_token=token,
                                video_path=str(video_path),
                                description=f"{title}\\n\\n{content}",
                                first_comment=first_comment
                            )"""

new_call = """                        # Call MetaReelPoster
                        try:
                            res = poster.publish_reel(
                                page_id=page_id,
                                page_token=token,
                                video_path=str(video_path),
                                description=f"{title}\\n\\n{content}",
                                first_comment=first_comment
                            )"""

if old_call in txt:
    txt = txt.replace(old_call, new_call)
    Path(r"D:\Highlight_Video_Studio\web\scheduled_publisher.py").write_text(txt, encoding="utf-8")
    print("Fixed page_token arg in scheduled_publisher.py!")
else:
    print("Could not find exact old_call in scheduled_publisher.py")
