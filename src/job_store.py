"""Atomic job snapshots with a durable retry journal for Windows file locks."""
from pathlib import Path
import copy
from functools import wraps
import json
import os
import sqlite3
import threading
import time
import uuid

from multi_pc.json_io import replace_with_retry, shared_reader

LOCK = threading.RLock()
_CACHE = {}
_FLUSHERS = set()


def transaction(action):
    @wraps(action)
    def wrapped(*args, **kwargs):
        with LOCK:
            return action(*args, **kwargs)
    return wrapped


def _journal(path):
    return Path(path).parent / "data" / "jobs_pending.sqlite3"


def _pending(path):
    journal = _journal(path)
    if not journal.exists():
        return None
    with sqlite3.connect(journal, timeout=10) as db:
        row = db.execute("SELECT payload FROM pending WHERE id=1").fetchone()
    return row[0] if row else None


def load(path):
    path = Path(path)
    with LOCK:
        pending = _pending(path)
        if pending is not None:
            return json.loads(pending)
        if not path.exists():
            return []
        stat = path.stat()
        signature = (stat.st_size, stat.st_mtime_ns)
        cached = _CACHE.get(str(path.resolve()))
        if cached and cached[0] == signature:
            return copy.deepcopy(cached[1])
        with shared_reader(path) as stream:
            text = stream.read()
        # Parse after closing the handle. An unreadable ledger is never an empty queue.
        rows = json.loads(text)
        if not isinstance(rows, list):
            raise ValueError("Job ledger must be a JSON array")
        _CACHE[str(path.resolve())] = (signature, rows)
        return copy.deepcopy(rows)


def _write(path, payload):
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        replace_with_retry(temporary, path, timeout=0.4)
    finally:
        temporary.unlink(missing_ok=True)


def flush(path):
    path = Path(path)
    with LOCK:
        payload = _pending(path)
        if payload is None:
            return True
        try:
            _write(path, payload)
        except PermissionError:
            return False
        with sqlite3.connect(_journal(path), timeout=10) as db:
            db.execute("DELETE FROM pending WHERE id=1")
        _CACHE.pop(str(path.resolve()), None)
        return True


def _persist(path, payload):
    journal = _journal(path)
    journal.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(journal, timeout=10) as db:
        db.execute("PRAGMA synchronous=FULL")
        db.execute("CREATE TABLE IF NOT EXISTS pending(id INTEGER PRIMARY KEY, payload TEXT NOT NULL)")
        db.execute("INSERT OR REPLACE INTO pending VALUES(1, ?)", (payload,))


def _retry_loop(path):
    key = str(path.resolve())
    try:
        while True:
            with LOCK:
                if flush(path):
                    _FLUSHERS.discard(key)
                    return
            time.sleep(2)
    finally:
        with LOCK:
            _FLUSHERS.discard(key)


def save(path, rows):
    path = Path(path)
    with LOCK:
        if not rows and path.exists() and path.stat().st_size > 100:
            return False
        payload = json.dumps(rows, ensure_ascii=False, indent=2)
        journal_exists = _pending(path) is not None
        if journal_exists:
            _persist(path, payload)
        try:
            _write(path, payload)
            if journal_exists:
                with sqlite3.connect(_journal(path), timeout=10) as db:
                    db.execute("DELETE FROM pending WHERE id=1")
        except PermissionError:
            _persist(path, payload)
            key = str(path.resolve())
            if key not in _FLUSHERS:
                _FLUSHERS.add(key)
                threading.Thread(target=_retry_loop, args=(path,), daemon=True, name="jobs-ledger-retry").start()
        _CACHE.pop(str(path.resolve()), None)
        return True
