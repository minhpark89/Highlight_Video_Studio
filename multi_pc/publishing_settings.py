"""Persist the operator's publishing parallelism independently of render jobs."""
import json
import threading
import uuid
from pathlib import Path

from multi_pc.json_io import replace_with_retry

MAX_POSTING_THREADS = 8
DEFAULT_POSTING_THREADS = 4
_LOCK = threading.RLock()


def load_publishing_settings(root):
    path = Path(root) / "data" / "publishing_settings.json"
    if not path.exists():
        return {"posting_threads": DEFAULT_POSTING_THREADS}
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    threads = value.get("posting_threads")
    if isinstance(threads, bool) or not isinstance(threads, int) or not 1 <= threads <= MAX_POSTING_THREADS:
        raise ValueError("Số luồng đăng phải từ 1 đến 8.")
    return {"posting_threads": threads}


def save_publishing_settings(root, threads):
    if isinstance(threads, bool) or not isinstance(threads, int) or not 1 <= threads <= MAX_POSTING_THREADS:
        raise ValueError("Số luồng đăng phải từ 1 đến 8.")
    path = Path(root) / "data" / "publishing_settings.json"
    with _LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temp.write_text(json.dumps({"posting_threads": threads}), encoding="utf-8")
            replace_with_retry(temp, path)
        finally:
            temp.unlink(missing_ok=True)
    return {"posting_threads": threads}


def credential_ready(entry):
    """Meta usage/cooldown is a gate, never a reason to switch credentials."""
    if not entry or entry.get("status") != "ACTIVE":
        return False
    if entry.get("rate_status") in ("COOLDOWN_80", "RATE_LIMITED"):
        return False
    try:
        return max(float(entry.get(key) or 0) for key in ("app_usage_pct", "cputime_pct", "time_pct")) < 80
    except (ValueError, TypeError):
        return False
