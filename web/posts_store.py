"""Fail-closed, atomic persistence for the scheduled-post queue."""

from __future__ import annotations

import json
import os
import threading
import uuid
from pathlib import Path


class PostsStoreError(RuntimeError):
    """Raised when the queue cannot be read or durably written."""


_LOCK = threading.RLock()


def _backup_path(path: Path) -> Path:
    return path.with_name(path.name + ".bak")


def _read_valid_list(path: Path) -> list:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError("posts queue root must be a JSON array")
    return value


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with open(temp, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass


def load_posts_file(path: str | Path) -> list:
    """Load the primary queue, recovering from a valid backup when necessary.

    Missing storage is a legitimate empty queue. A present but malformed primary
    never degrades to ``[]``: recovery is attempted, otherwise an explicit error
    is raised so callers cannot overwrite an unknown queue state.
    """
    primary = Path(path)
    backup = _backup_path(primary)
    with _LOCK:
        if not primary.exists():
            if backup.exists():
                try:
                    recovered = _read_valid_list(backup)
                    _atomic_write_bytes(primary, backup.read_bytes())
                    return recovered
                except Exception as exc:
                    raise PostsStoreError(f"posts queue backup is unreadable: {exc}") from exc
            return []
        try:
            return _read_valid_list(primary)
        except Exception as primary_exc:
            if backup.exists():
                try:
                    recovered = _read_valid_list(backup)
                    _atomic_write_bytes(primary, backup.read_bytes())
                    return recovered
                except Exception as backup_exc:
                    raise PostsStoreError(
                        f"posts queue primary and backup are unreadable: primary={primary_exc}; backup={backup_exc}"
                    ) from backup_exc
            raise PostsStoreError(f"posts queue is unreadable and has no valid backup: {primary_exc}") from primary_exc


def save_posts_file(path: str | Path, posts: list) -> None:
    """Atomically replace the queue and mirror the same valid revision to backup."""
    if not isinstance(posts, list):
        raise PostsStoreError("refusing to save posts queue: value is not a list")
    primary = Path(path)
    backup = _backup_path(primary)
    payload = json.dumps(posts, indent=2, ensure_ascii=False).encode("utf-8")
    with _LOCK:
        _atomic_write_bytes(primary, payload)
        _atomic_write_bytes(backup, payload)
