"""Durable, bounded background requests for explicit video recovery actions."""
from datetime import datetime
from pathlib import Path
import copy
import threading
import time
import uuid

from src.video_recovery_media import read_json, write_json
from web.meta_diagnostics import safe_error

_LOCK = threading.RLock()
_ACTIVE = set()
_SLOTS = threading.BoundedSemaphore(2)
PENDING = {"queued", "running", "waiting_worker"}


def _path(root):
    return Path(root) / "data" / "video_recovery_requests.json"


def operation_for(root, post_id):
    with _LOCK:
        return copy.deepcopy(read_json(_path(root), {}).get(post_id))


def _update(root, post_id, **changes):
    with _LOCK:
        rows = read_json(_path(root), {})
        rows[post_id].update(changes, updated_at=datetime.now().isoformat(timespec="seconds"))
        write_json(_path(root), rows)
        return copy.deepcopy(rows[post_id])


def enqueue(root, post_id, body, *, kind="auto"):
    root = Path(root).resolve()
    key = (str(root), post_id)
    permitted = ("filename", "mode", "schedule_time", "video_id", "render_if_missing")
    payload = {name: body[name] for name in permitted if name in body}
    with _LOCK:
        rows = read_json(_path(root), {})
        previous = rows.get(post_id)
        if previous and previous.get("status") in PENDING:
            if previous.get("payload") != payload or previous.get("kind") != kind:
                raise ValueError("Yêu cầu phục hồi trước đang chạy; chờ kết quả trước khi đổi clip hoặc giờ đăng.")
            operation = previous
        else:
            operation = {"id": uuid.uuid4().hex, "post_id": post_id, "kind": kind,
                         "payload": payload, "status": "queued",
                         "created_at": datetime.now().isoformat(timespec="seconds"),
                         "message": "Đã nhận yêu cầu; đang tìm và kiểm tra MP4 phù hợp."}
            rows[post_id] = operation
            write_json(_path(root), rows)
        if key not in _ACTIVE:
            _ACTIVE.add(key)
            thread = threading.Thread(target=_run, args=(root, post_id),
                                      daemon=True, name="video-recovery-request")
            try:
                thread.start()
            except Exception:
                _ACTIVE.discard(key)
                raise
        return copy.deepcopy(operation)


def progress(root, post_id, message):
    if operation_for(root, post_id):
        _update(root, post_id, message=message)


def _run(root, post_id):
    from web import app as api

    key = (str(root), post_id)
    try:
        with _SLOTS, api.app.app_context():
            while True:
                operation = operation_for(root, post_id)
                if not operation or operation.get("status") not in PENDING:
                    return
                body = dict(operation["payload"])
                _update(root, post_id, status="running", message="Đang kiểm tra clip, nguồn và trạng thái Meta.")
                if operation["kind"] == "replace":
                    body["confirm_replace_failed_video"] = True
                    response = api.api_replace_failed_video(post_id, _body=body)
                else:
                    response = api.api_auto_recover_failed_video(post_id, _body=body)
                response = response[0] if isinstance(response, tuple) else response
                result = response.get_json()
                if result.get("busy"):
                    _update(root, post_id, status="waiting_worker",
                            message="MP4 đã tìm thấy; đang chờ worker tiếp nhận yêu cầu.")
                    time.sleep(1)
                    continue
                success = bool(result.get("success"))
                _update(root, post_id, status="complete" if success else "error", result=result,
                        message=result.get("message") or result.get("error") or "Đã xử lý yêu cầu.")
                return
    except Exception as exc:
        _update(root, post_id, status="error", message=safe_error(exc))
    finally:
        with _LOCK:
            _ACTIVE.discard(key)


def resume_pending(root):
    with _LOCK:
        rows = copy.deepcopy(read_json(_path(root), {}))
    for post_id, operation in rows.items():
        if operation.get("status") in PENDING:
            enqueue(root, post_id, operation["payload"], kind=operation["kind"])
