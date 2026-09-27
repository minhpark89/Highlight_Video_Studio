"""Persistent queue for first comments on Meta-scheduled Reels."""

from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent
QUEUE_FILE = BASE_DIR / "data" / "pending_first_comments.json"
_LOCK = threading.Lock()


def _load_unlocked():
    if not QUEUE_FILE.exists():
        return []
    try:
        value = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except Exception:
        return []


def _save_unlocked(items):
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = QUEUE_FILE.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(QUEUE_FILE)


def enqueue_first_comment(object_id, page_token, comment_text, due_at, token_id=None):
    item = {
        "id": f"fc_{uuid.uuid4().hex[:12]}",
        "object_id": str(object_id),
        "page_token": str(page_token),
        "token_id": str(token_id or ""),
        "comment_text": str(comment_text),
        "due_at": int(due_at),
        "attempts": 0,
        "status": "pending",
        "last_error": "",
    }
    with _LOCK:
        items = _load_unlocked()
        items.append(item)
        _save_unlocked(items)
    return {"success": True, "pending": True, "queue_id": item["id"], "due_at": item["due_at"]}


def process_due_first_comments(poster, now=None):
    current = int(now or time.time())
    changed = False
    completed = 0
    with _LOCK:
        items = _load_unlocked()
        for item in items:
            if item.get("status") != "pending" or int(item.get("due_at") or 0) > current:
                continue
            result = poster.post_first_comment(
                item.get("object_id"),
                item.get("page_token"),
                item.get("comment_text"),
                token_id=item.get("token_id") or None,
            )
            item["attempts"] = int(item.get("attempts") or 0) + 1
            if result.get("success"):
                item["status"] = "posted"
                item["comment_id"] = result.get("comment_id")
                item["posted_at"] = current
                # Do not retain access tokens after the comment succeeds.
                item["page_token"] = ""
                completed += 1
            elif item["attempts"] >= 8:
                item["status"] = "failed"
                item["last_error"] = result.get("error", "Unknown error")
                item["page_token"] = ""
            else:
                item["last_error"] = result.get("error", "Unknown error")
                delay = min(900, 30 * (2 ** (item["attempts"] - 1)))
                item["due_at"] = current + delay
            changed = True
        # Retain a compact audit trail and discard old successful entries.
        items = [
            item for item in items
            if item.get("status") != "posted" or current - int(item.get("posted_at") or current) < 86400
        ]
        if changed:
            _save_unlocked(items)
    return {"processed": completed, "changed": changed}
