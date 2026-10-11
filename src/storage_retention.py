"""Local media retention; publication and job ledgers remain the authority."""
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import re
import threading
import uuid

from multi_pc.json_io import replace_with_retry

DEFAULTS = {'delete_published_reels': True, 'delete_completed_sources': True}
_LOCK = threading.RLock()
_WORKER = None
_JOB_NAME = re.compile(r'^(job_\d+_[A-Za-z0-9]+)(?:[._-]|$)')
_SOURCE_EXTENSIONS = {'.mp4', '.mkv', '.webm', '.mov', '.m4a', '.mp3', '.wav', '.part', '.ytdl'}


def validate_settings(value):
    if not isinstance(value, dict) or set(value) - DEFAULTS.keys():
        raise ValueError('Invalid storage retention settings')
    if any(type(enabled) is not bool for enabled in value.values()):
        raise ValueError('Storage retention options must be true or false')
    return dict(value)


def settings(root):
    path = Path(root) / 'config.json'
    if not path.exists():
        return dict(DEFAULTS)
    config = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(config, dict):
        raise ValueError('Configuration must be an object')
    return {**DEFAULTS, **validate_settings(config.get('storage_retention', {}))}


def safe_file(value, root):
    """Return a regular file inside root, rejecting links and junctions."""
    root = Path(root).absolute()
    original = Path(value)
    if not original.is_absolute():
        original = root / original
    original = original.absolute()
    candidate = original.resolve()
    boundary = root.resolve()
    if not candidate.is_relative_to(boundary) or candidate == boundary:
        return None
    for path in (original, *original.parents):
        try:
            stat = path.lstat()
            if path.is_symlink() or getattr(stat, 'st_file_attributes', 0) & 0x400:
                return None
        except FileNotFoundError:
            return None
        if path == root:
            break
    return candidate if candidate.is_file() else None


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        replace_with_retry(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def cleanup_statistics(root):
    path = Path(root) / 'data/storage_cleanup.json'
    if not path.exists():
        return {'published_reels_deleted': 0, 'source_files_deleted': 0, 'freed_bytes': 0, 'last_cleanup_at': ''}
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict):
        raise ValueError('Cleanup statistics unreadable')
    return value


def record_cleanup(root, kind, count, size):
    """Statistics failure never changes a confirmed publication result."""
    try:
        with _LOCK:
            state = cleanup_statistics(root)
            key = 'published_reels_deleted' if kind == 'published_reel' else 'source_files_deleted'
            state[key] = int(state.get(key, 0)) + count
            state['freed_bytes'] = int(state.get('freed_bytes', 0)) + size
            state['last_cleanup_at'] = datetime.now().isoformat(timespec='seconds')
            _write(Path(root) / 'data/storage_cleanup.json', state)
    except (OSError, ValueError, TypeError):
        pass


def _referenced_names(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from _referenced_names(child)
    elif isinstance(value, list):
        for child in value:
            yield from _referenced_names(child)
    elif isinstance(value, str):
        name = value.replace('\\', '/').split('/')[-1]
        if _JOB_NAME.match(name):
            yield name


def active_packages(root, *, queue_file=None):
    """Read consumers strictly: unreadable state must never authorize deletion."""
    from multi_pc.json_io import shared_reader
    path = Path(queue_file) if queue_file is not None else Path(root) / 'data/content_packages.json'
    if not path.exists():
        return []
    with shared_reader(path) as stream:
        rows = json.load(stream)
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError('Content queue must be an array of objects')
    return rows


def cleanup_completed_sources(root, *, job_id=None, packages=None):
    """Delete source media only while its current job is durably completed."""
    from src import job_store
    from web.posts_store import load_posts_file

    root = Path(root)
    result = {'deleted_count': 0, 'freed_bytes': 0, 'errors': 0}
    if not settings(root)['delete_completed_sources']:
        return result
    posts = load_posts_file(root / 'posts.json')
    protected = set()
    recovery_jobs = set()
    for post in posts:
        if post.get('status') not in ('published', 'superseded', 'cancelled'):
            protected.update(_referenced_names(post))
    for package in active_packages(root) if packages is None else packages:
        if package.get('status') in ('queued', 'running', 'retryable'):
            protected.update(_referenced_names(package))
    # Recovery provenance does not consume raw media. Active render requests do.
    for name in ('video_recovery_tasks.json', 'video_recovery_requests.json'):
        path = root / 'data' / name
        if path.is_file():
            rows = json.loads(path.read_text(encoding='utf-8-sig'))
            if isinstance(rows, dict):
                rows = list(rows.values())
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise ValueError('Recovery queue must be an array of objects')
            for row in rows:
                if row.get('status') not in ('completed', 'ready', 'cancelled', 'superseded'):
                    protected.update(_referenced_names(row))
                    recovery_jobs.update(_JOB_NAME.match(name).group(1) for name in _referenced_names(row))
    ledger = root / 'jobs.json'
    with job_store.LOCK:
        jobs = job_store.load(ledger)
        completed = {job['id']: job for job in jobs if job.get('status') == 'completed'
                     and (job_id is None or job.get('id') == job_id)}
        changed = {}
        for area in ('downloads', 'temp'):
            directory = root / area
            if not directory.is_dir():
                continue
            for entry in directory.iterdir():
                match = _JOB_NAME.match(entry.name)
                if (not match or match.group(1) not in completed or entry.name in protected
                        or match.group(1) in recovery_jobs
                        or entry.suffix.lower() not in _SOURCE_EXTENSIONS):
                    continue
                try:
                    candidate = safe_file(entry, directory)
                    if not candidate:
                        continue
                    stat = candidate.stat()
                    # Verify the job under the same lock used by retry/cancel.
                    if completed[match.group(1)].get('status') != 'completed':
                        continue
                    candidate.unlink()
                    result['deleted_count'] += 1
                    result['freed_bytes'] += stat.st_size
                    changed[match.group(1)] = changed.get(match.group(1), 0) + stat.st_size
                except OSError:
                    result['errors'] += 1
        if changed:
            stamp = datetime.now().isoformat(timespec='seconds')
            for jid, size in changed.items():
                job = completed[jid]
                job['source_media_deleted_at'] = stamp
                job['source_media_deleted_bytes'] = int(job.get('source_media_deleted_bytes', 0)) + size
            job_store.save(ledger, jobs)
    if result['deleted_count']:
        record_cleanup(root, 'completed_source', result['deleted_count'], result['freed_bytes'])
    return result


def cleanup_cycle(root):
    """Local retention must never wait for the scheduler's network requests."""
    from web import scheduled_publisher
    with _LOCK:
        sources = cleanup_completed_sources(root)
        posts = scheduled_publisher.load_posts()
        reels = scheduled_publisher.cleanup_published_clip_files(posts)
        if reels['deleted_count']:
            scheduled_publisher.save_posts(posts)
        return {'sources': sources, 'reels': reels}


def start_storage_retention_worker(root):
    global _WORKER
    if _WORKER is not None and _WORKER.is_alive():
        return _WORKER
    root = Path(root).resolve()
    def run():
        from multi_pc.data_root import ProcessLease
        from web.scheduled_publisher import sanitize_error
        lease = ProcessLease('storage-retention', root, stale_after=120)
        try:
            if not lease.acquire():
                return
            while True:
                try:
                    cleanup_cycle(root)
                except Exception as exc:
                    logging.getLogger(__name__).warning('Storage cleanup deferred: %s', sanitize_error(exc))
                threading.Event().wait(20)
        finally:
            lease.release()
    _WORKER = threading.Thread(target=run, name='storage-retention', daemon=True)
    _WORKER.start()
    return _WORKER
