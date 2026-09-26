import sys
from pathlib import Path
HVS_DIR = Path(r"D:\Highlight_Video_Studio")
sys.path.insert(0, str(HVS_DIR))

from src.publisher.website_publisher import (
    publish_clip_to_website_cms,
    generate_curiosity_comment_with_llm,
    get_clip_metadata
)

clip = "job_1789889585_ca8470_clip_1.mp4"
meta = get_clip_metadata(clip)
print("Metadata:", meta)

# 1. Test live article creation with embedded HTML5 video player to bestnews.cfx.bz
url = publish_clip_to_website_cms(clip)
print("Published Article URL:", url)

# 2. Test LLM Curiosity Comment with fallback
comment_llm = generate_curiosity_comment_with_llm(meta["video_title"], url, enable_llm=True)
print("\nFirst Comment (LLM=True):")
print(comment_llm)

comment_fixed = generate_curiosity_comment_with_llm(meta["video_title"], url, enable_llm=False)
print("\nFirst Comment (LLM=False fallback):")
print(comment_fixed)
