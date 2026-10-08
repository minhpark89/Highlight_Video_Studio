"""Keep known malformed historical highlights out of automatic publication."""
from pathlib import Path
import threading

from src import job_store

_LOCK = threading.RLock()
_CACHE = {}


def short_clip_errors(jobs):
    errors = {}
    for job in jobs:
        for clip in job.get("clips", []):
            try:
                duration = float(clip.get("duration") or float(clip["end"]) - float(clip["start"]))
                long_source = float(job.get("duration") or 0) >= 60
            except (ValueError, TypeError, KeyError):
                continue
            if long_source and 0 < duration < 5 and clip.get("filename"):
                errors[clip["filename"]] = (
                    f"Clip chỉ dài {duration:.1f} giây; mốc cắt cũ không hợp lệ. "
                    "Cần render lại và kiểm tra trước khi đăng.")
    return errors


def _signature(path):
    try:
        stat = path.stat()
        return stat.st_size, stat.st_mtime_ns
    except FileNotFoundError:
        return None


def clip_error(path, post=None):
    if (post or {}).get("media_quality_error"):
        return post["media_quality_error"]
    path = Path(path)
    root = path.parent.parent.resolve()
    ledger = root / "jobs.json"
    signature = (_signature(ledger), _signature(root / "data" / "jobs_pending.sqlite3"))
    with _LOCK:
        cached = _CACHE.get(str(root))
        if not cached or cached[0] != signature:
            errors = short_clip_errors(job_store.load(ledger))
            if len(_CACHE) > 16:
                _CACHE.clear()
            _CACHE[str(root)] = signature, errors
        return _CACHE[str(root)][1].get(path.name, "")


def require_publishable(path, post=None):
    reason = clip_error(path, post)
    if reason:
        raise ValueError(reason)
