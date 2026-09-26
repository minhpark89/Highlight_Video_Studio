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

print("\n--- Testing publish_clip_to_website_cms ---")
article_url = publish_clip_to_website_cms(clip)
print("Article URL:", article_url)

print("\n--- Testing generate_curiosity_comment_with_llm (LLM=True) ---")
comment_llm = generate_curiosity_comment_with_llm(meta["video_title"], article_url, enable_llm=True)
print("LLM Comment:\n", comment_llm)

print("\n--- Testing generate_curiosity_comment_with_llm (LLM=False) ---")
comment_fixed = generate_curiosity_comment_with_llm(meta["video_title"], article_url, enable_llm=False)
print("Fixed Fallback Comment:\n", comment_fixed)
