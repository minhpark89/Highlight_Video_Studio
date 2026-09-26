import sys
from pathlib import Path
HVS_DIR = Path(r"D:\Highlight_Video_Studio")
sys.path.insert(0, str(HVS_DIR))

from src.publisher.website_publisher import (
    publish_clip_to_website_cms,
    generate_curiosity_comment_with_llm,
    get_clip_metadata
)

clip = "job_1790182893_f5d241_clip_2.mp4"
print("Testing live publishing with full upgrade...")
article_url, hero_img = publish_clip_to_website_cms(clip)
print("=== RESULT ===")
print("Article URL:", article_url)
print("Hero Image:", hero_img)

meta = get_clip_metadata(clip)
print("Title:", meta["video_title"])

comment = generate_curiosity_comment_with_llm(meta["video_title"], article_url, enable_llm=True)
print("First Comment:\n", comment)
