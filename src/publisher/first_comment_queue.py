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


def enqueue_first_comment(object_id, page_token, comment_text, due_at, token_id=None, post_id=None, meta_video_id=None, outcome_unknown=False):
    text = str(comment_text or "").strip()
    item = {
        "id": f"fc_{uuid.uuid4().hex[:12]}",
        "object_id": str(object_id),
        "meta_video_id": str(meta_video_id or object_id),
        "page_token": str(page_token),
        "token_id": str(token_id or ""),
        "comment_text": text,
        "due_at": int(due_at),
        "attempts": 0,
        "status": "verification_pending" if outcome_unknown else "pending",
        "last_error": "",
        "post_id": str(post_id or ""),
    }
    with _LOCK:
        items = _load_unlocked()
        if post_id:
            existing = next((entry for entry in items if entry.get("post_id") == str(post_id)
                             and entry.get("status") in ("pending", "posted", "verification_pending")), None)
            if existing:
                return {"success": True, "pending": existing.get("status") == "pending",
                        "queue_id": existing["id"], "due_at": existing.get("due_at")}
        items.append(item)
        _save_unlocked(items)
    return {"success": True, "pending": not outcome_unknown, "outcome_unknown": outcome_unknown,
            "queue_id": item["id"], "due_at": item["due_at"]}


def cancel_first_comment(post_id=None, queue_id=None, object_id=None):
    """Stop pending comments for a cancelled schedule; retain posted history."""
    keys = {str(value) for value in (post_id, queue_id, object_id) if value}
    if not keys:
        return {"cancelled": 0}
    cancelled = 0
    with _LOCK:
        # Corrupt data must block local removal rather than silently lose a queue.
        items = json.loads(QUEUE_FILE.read_text(encoding="utf-8")) if QUEUE_FILE.exists() else []
        if not isinstance(items, list):
            raise ValueError("Invalid First Comment queue")
        for item in items:
            if not keys.intersection({str(item.get("post_id") or ""), str(item.get("id") or ""),
                                      str(item.get("object_id") or ""), str(item.get("meta_video_id") or "")}):
                continue
            if item.get("status") in ("pending", "verification_pending", "pending_retry"):
                item.update(status="cancelled", cancelled_at=int(time.time()),
                            last_error="Meta schedule cancelled by the operator.", page_token="")
                cancelled += 1
        if cancelled:
            _save_unlocked(items)
    return {"cancelled": cancelled}


def process_due_first_comments(poster, now=None, prepare=None):
    current = int(now or time.time())
    changed = False
    completed = 0
    outcomes = []
    with _LOCK:
        items = _load_unlocked()
        for item in items:
            if item.get("status") != "pending" or int(item.get("due_at") or 0) > current:
                continue
            if prepare is not None:
                try:
                    readiness = prepare(item)
                except Exception:
                    readiness = {"ready": False, "error": "Exact credential or publication verification unavailable."}
                if not readiness.get("ready"):
                    item["last_error"] = readiness.get("error", "Waiting for verified Reel publication.")
                    item["due_at"] = current + 60
                    changed = True
                    continue
                if readiness.get("page_token"):
                    item["page_token"] = readiness["page_token"]
            try:
                result = poster.post_first_comment(
                    item.get("object_id"),
                    item.get("page_token"),
                    item.get("comment_text"),
                    token_id=item.get("token_id") or None,
                )
            except Exception as exc:
                result = {"success": False, "error": str(exc)}
            item["attempts"] = int(item.get("attempts") or 0) + 1
            if result.get("success"):
                item["status"] = "posted"
                item["comment_id"] = result.get("comment_id")
                item["posted_at"] = current
                # Do not retain access tokens after the comment succeeds.
                item["page_token"] = ""
                completed += 1
            elif result.get("outcome_unknown"):
                item["status"] = "verification_pending"
                item["last_error"] = "Comment request outcome is unknown; verify on Meta before retrying."
            else:
                item["last_error"] = result.get("error", "Unknown error")
                # Definite rejections can recover after provider cooldowns or
                # credential restoration. Do not abandon them after eight tries.
                delay = min(900, 30 * (2 ** min(item["attempts"] - 1, 5)))
                item["due_at"] = current + delay
            outcomes.append({
                "queue_id": item.get("id"),
                "post_id": item.get("post_id") or "",
                "status": item.get("status"),
                "attempts": item.get("attempts"),
                "comment_id": item.get("comment_id"),
                "last_error": item.get("last_error", ""),
                "due_at": item.get("due_at"),
            })
            changed = True
        # Retain a compact audit trail and discard old successful entries.
        items = [
            item for item in items
            if item.get("status") != "posted" or current - int(item.get("posted_at") or current) < 86400
        ]
        if changed:
            _save_unlocked(items)
    return {"processed": completed, "changed": changed, "outcomes": outcomes}
