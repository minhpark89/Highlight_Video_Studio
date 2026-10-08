"""Preserve completed clips when retrying an interrupted render job."""
from pathlib import Path
import math


def valid_plan(plan, count, duration):
    if not isinstance(plan, list) or len(plan) != count:
        return False
    try:
        return all(math.isfinite(float(h["start"])) and math.isfinite(float(h["end"]))
                   and 0 <= float(h["start"]) < float(h["end"]) <= duration + 0.1
                   and float(h["end"]) - float(h["start"]) >= min(15, duration) for h in plan)
    except (KeyError, TypeError, ValueError):
        return False


def completed_clip(job, index, highlight, output_dir):
    clip = next((c for c in job.get("clips", []) if c.get("clip_index") == index), None)
    if not clip:
        return None
    if any(abs(float(clip.get(key, -1)) - float(highlight[key])) > 0.1 for key in ("start", "end")):
        raise ValueError("Mốc cắt đã thay đổi so với clip xuất trước; giữ clip cũ để kiểm tra, không ghi đè.")
    path = Path(output_dir) / clip["filename"]
    if path.is_file():
        from src.render_quality import validate_render
        validate_render(path, highlight["end"] - highlight["start"], decode=False)
        return dict(clip)
    from web.posts_store import load_posts_file
    posts = load_posts_file(Path(output_dir).parent / "posts.json")
    if any(p.get("status") == "published" and
           (p.get("media_file") or p.get("clip_filename")) == clip["filename"] for p in posts):
        return dict(clip)
    return None
