import sys
from pathlib import Path
HVS_DIR = Path(r"D:\Highlight_Video_Studio")
sys.path.insert(0, str(HVS_DIR))

from src.publisher.website_publisher import (
    publish_clip_to_website_cms,
    generate_curiosity_comment_with_llm,
    get_clip_metadata
)

# Check clip metadata
clip = "job_1790182893_f5d241_clip_2.mp4"
meta = get_clip_metadata(clip)
print("Meta:", meta)
print("Long video path:", meta.get("long_video_path"))
