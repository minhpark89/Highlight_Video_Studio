"""Fail-closed, atomic persistence for the scheduled-post queue."""

from __future__ import annotations

import json
import os
import threading
import uuid
import copy
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from multi_pc.json_io import replace_with_retry


class PostsStoreError(RuntimeError):
    """Raised when the queue cannot be read or durably written."""


_LOCK = threading.RLock()
_READS = threading.local()
_VIEW_LOCK = threading.RLock()
_VIEWS = OrderedDict()


def _revision(stat):
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def posts_snapshot(path: str | Path):
    """Borrow a read-only revision for views; copy selected rows before editing.

    There is no TTL. Stat on every request detects writes and atomic replacement.
    This cache never carries writable baselines and never takes the writer lock
    on the healthy read path. Corruption still uses the store's backup recovery.
    """
    primary = resolve_posts_file(path)
    key = str(primary.resolve())
    with _VIEW_LOCK:
        for _ in range(3):
            try:
                revision = _revision(primary.stat())
                cached = _VIEWS.get(key)
                if cached and cached[0] == revision:
                    _VIEWS.move_to_end(key)
                    return cached[1]
                with primary.open("rb") as handle:
                    before = _revision(os.fstat(handle.fileno()))
                    payload = handle.read()
                    after = _revision(os.fstat(handle.fileno()))
                if before != after or after != _revision(primary.stat()):
                    continue
                rows = json.loads(payload)
                if not isinstance(rows, list):
                    raise ValueError("posts queue root must be a JSON array")
                _VIEWS[key] = (after, rows)
                _VIEWS.move_to_end(key)
                while len(_VIEWS) > 4:
                    _VIEWS.popitem(last=False)
                return rows
            except (OSError, ValueError):
                break
        _VIEWS.pop(key, None)
        # Recovery and fail-closed behavior remain identical to writable reads.
        return list(load_posts_file(primary))


class PostsList(list):
    """A queue revision carrying its original rows for conflict aware saves."""
    def __init__(self, rows, path):
        super().__init__(rows)
        self._store_path = str(path.resolve())
        self._baseline = copy.deepcopy(rows)


def _remember(path, rows):
    value = PostsList(rows, path)
    if not hasattr(_READS, "baselines"):
        _READS.baselines = {}
    _READS.baselines[str(path.resolve())] = copy.deepcopy(rows)
    return value


def _merge_revision(current, incoming, baseline):
    """Apply only fields changed since load; preserve independent worker edits."""
    old = {str(row.get("id")): row for row in baseline if isinstance(row, dict) and row.get("id")}
    now = {str(row.get("id")): row for row in current if isinstance(row, dict) and row.get("id")}
    new = {str(row.get("id")): row for row in incoming if isinstance(row, dict) and row.get("id")}
    if len(old) != len(baseline) or len(now) != len(current) or len(new) != len(incoming):
        raise PostsStoreError("posts queue rows require unique nonempty ids")
    if len(set(old)) != len(baseline) or len(set(now)) != len(current) or len(set(new)) != len(incoming):
        raise PostsStoreError("posts queue contains duplicate ids")
    for post_id in old.keys() - new.keys():
        now.pop(post_id, None)
    for post_id, incoming_row in new.items():
        if post_id not in old:
            now[post_id] = copy.deepcopy(incoming_row)
            continue
        if post_id not in now:
            # A concurrent explicit deletion wins over an old worker snapshot.
            continue
        original = old[post_id]
        target = now[post_id]
        frozen_before_merge = bool(target.get("content_frozen_at") and not original.get("content_frozen_at"))
        protected = target.get("status") in ("published", "processing") and incoming_row.get("status") not in ("published", "processing")
        for key in set(original) | set(incoming_row):
            if original.get(key) == incoming_row.get(key) and (key in original) == (key in incoming_row):
                continue
            if protected and target.get(key) != original.get(key) and key in ("status", "post_fb_id", "fb_url", "meta_post_id", "meta_upload_video_id", "retryable", "retry_stage", "error"):
                continue
            # An approval/publish claim can race a slow content response. A
            # worker revision loaded before the freeze cannot replace the
            # caption, website or comment version that was approved.
            if frozen_before_merge and key in (
                "title", "content", "hashtags", "first_comment", "first_comment_snapshot", "article_url",
                "content_package_id", "content_package_source", "website_status", "website_error",
                "website_video_status", "website_video_url", "first_comment_source"):
                continue
            if key in incoming_row:
                target[key] = copy.deepcopy(incoming_row[key])
            else:
                target.pop(key, None)
    order = list(dict.fromkeys([str(row["id"]) for row in incoming if isinstance(row, dict)] +
                               [str(row["id"]) for row in current if isinstance(row, dict)]))
    return [now[post_id] for post_id in order if post_id in now]


def resolve_posts_file(path=None) -> Path:
    """Resolve an explicit queue path, falling back to the canonical root.

    An explicit ``path`` is honoured verbatim so a caller that legitimately owns a
    scoped queue file (tests, restored fixtures, a migration script) is not
    hijacked. Callers that pass nothing get the one canonical path for this
    installation, which is what stops a packaged launcher and a dev server from
    forking the live queue.
    """
    if path is not None and str(path).strip():
        return Path(path)
    return canonical_posts_file()


def canonical_posts_file() -> Path:
    """Return the one canonical queue path for this installation.

    A packaged launcher, a reloaded dev server and the background worker each
    compute their own module path; without one canonical root they would read and
    write different queue files and silently drop scheduled posts.
    """
    configured = str(os.environ.get("HIGHLIGHT_DATA_ROOT") or "").strip()
    root = Path(configured).expanduser() if configured else Path(__file__).resolve().parent.parent
    root = root.resolve()
    allowed = Path(__file__).resolve().parent.parent.resolve()
    if configured and root != allowed:
        raise PostsStoreError(
            f"HIGHLIGHT_DATA_ROOT ({root}) does not match this installation ({allowed})"
        )
    root.mkdir(parents=True, exist_ok=True)
    return root / "posts.json"


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
        replace_with_retry(temp, path)
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
    primary = resolve_posts_file(path)
    backup = _backup_path(primary)
    with _LOCK:
        if not primary.exists():
            if backup.exists():
                try:
                    recovered = _read_valid_list(backup)
                    _atomic_write_bytes(primary, backup.read_bytes())
                    return _remember(primary, recovered)
                except Exception as exc:
                    raise PostsStoreError(f"posts queue backup is unreadable: {exc}") from exc
            return _remember(primary, [])
        try:
            return _remember(primary, _read_valid_list(primary))
        except Exception as primary_exc:
            if backup.exists():
                try:
                    recovered = _read_valid_list(backup)
                    _atomic_write_bytes(primary, backup.read_bytes())
                    return _remember(primary, recovered)
                except Exception as backup_exc:
                    raise PostsStoreError(
                        f"posts queue primary and backup are unreadable: primary={primary_exc}; backup={backup_exc}"
                    ) from backup_exc
            raise PostsStoreError(f"posts queue is unreadable and has no valid backup: {primary_exc}") from primary_exc


def save_posts_file(path: str | Path, posts: list) -> None:
    """Atomically replace the queue and mirror the same valid revision to backup."""
    if not isinstance(posts, list):
        raise PostsStoreError("refusing to save posts queue: value is not a list")
    primary = resolve_posts_file(path)
    backup = _backup_path(primary)
    source_posts = posts
    incoming_snapshot = copy.deepcopy(list(posts))
    with _LOCK:
        if isinstance(posts, PostsList) and posts._store_path == str(primary.resolve()):
            baseline = posts._baseline
        else:
            baseline = getattr(_READS, "baselines", {}).get(str(primary.resolve()))
        if baseline is not None and primary.exists():
            posts = _merge_revision(_read_valid_list(primary), posts, baseline)
        payload = json.dumps(posts, indent=2, ensure_ascii=False).encode("utf-8")
        # Preserve the last populated ledger before a clear/delete or a stale
        # writer replaces it. The rolling .bak mirrors the new revision and
        # cannot recover an accidental empty write after it happens.
        if primary.exists():
            previous = _read_valid_list(primary)
            old_ids = {str(row.get("id")) for row in previous if isinstance(row, dict)}
            new_ids = {str(row.get("id")) for row in posts if isinstance(row, dict)}
            if old_ids - new_ids:
                archive = primary.with_name(
                    f"{primary.stem}.history.{datetime.now().strftime('%Y%m%d_%H%M%S')}.{uuid.uuid4().hex[:6]}.json"
                )
                _atomic_write_bytes(archive, primary.read_bytes())
        _atomic_write_bytes(primary, payload)
        _atomic_write_bytes(backup, payload)
        if isinstance(source_posts, PostsList):
            source_posts._baseline = incoming_snapshot
        if hasattr(_READS, "baselines"):
            _READS.baselines[str(primary.resolve())] = incoming_snapshot
