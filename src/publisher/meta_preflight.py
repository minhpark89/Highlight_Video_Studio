"""Fail-closed Meta Page/token mapping preflight.

The module only consumes Page mappings produced by ``/me/accounts`` discovery.
It never substitutes a generic credential and never performs a publish probe.
"""
from __future__ import annotations

import re
from src.publisher.meta_api import REEL_REQUIRED_PERMISSIONS, COMMENT_REQUIRED_PERMISSIONS

# Retain the specific legacy NPE aliases already stored by older builds.
# MANAGE assigns tasks; it does not by itself prove CREATE_CONTENT or MODERATE.
PUBLISH_TASKS = {"CREATE_CONTENT", "PROFILE_PLUS_CREATE_CONTENT"}
COMMENT_TASKS = {"MODERATE", "PROFILE_PLUS_MODERATE"}

_SECRET_PATTERNS = (
    re.compile(r"(access_token|page_token|token|api_key|secret|password|authorization)[=:\s]+[^\s&\"',]+", re.I),
    re.compile(r"([?&](?:access_token|token|api_key|key)=)[^\s&\"']+", re.I),
    re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]+", re.I),
)

_ACTIONS = {
    'missing_page': 'Sync lại danh sách Page từ credential trước khi lên lịch.',
    'missing_mapping': 'Page chưa có mapping được Meta xác minh; hãy Sync Page từ credential quản lý Page này.',
    'missing_credential': 'Credential nguồn không còn trong Token Vault; hãy thêm lại và Sync Page.',
    'stale_credential': 'Credential nguồn không còn hoạt động; hãy kết nối lại và Sync Page.',
    'stale_mapping': 'Mapping Page-token đã cũ sau khi credential thay đổi; hãy Refresh Pages.',
    'cross_bound_mapping': 'Token được chọn không thuộc Page này; hãy chọn mapping đã được Sync cho đúng page_id.',
    'publish_capability_missing': 'Credential không có quyền tạo nội dung cho Page; hãy cấp lại quyền Meta rồi Refresh Pages.',
    'comment_capability_missing': 'First Comment cần tác vụ MODERATE trên Page; hãy cấp quyền bình luận rồi Refresh Pages.',
    'permissions_missing': 'Credential thiếu scope cho thao tác này; hãy cấp quyền Meta đúng chức năng rồi Refresh Pages.',
    'page_access_refresh_failed': 'Chưa làm mới được quyền truy cập Page; kiểm tra lỗi Meta và Refresh Pages trước khi gửi bài.',
}


def sanitize_text(value, limit=400):
    text = str(value or "")
    for pattern in _SECRET_PATTERNS:
        if pattern.groups >= 2:
            text = pattern.sub(lambda match: match.group(1) + "[redacted]", text)
        else:
            text = pattern.sub("[redacted]", text)
    return " ".join(text.split())[:limit]


def mapping_error(page_id, page_name, code, *, stage="mapping", token_id="", detail=""):
    action = _ACTIONS.get(code, 'Refresh credential và Sync lại Page trước khi lên lịch.')
    return {
        "ok": False,
        "page_id": str(page_id or ""),
        "page_name": str(page_name or page_id or ""),
        "token_id": str(token_id or ""),
        "stage": stage,
        "code": code,
        "action": action,
        "detail": sanitize_text(detail),
        "reconnect_required": True,
        "facebook_error": {
            "stage": stage,
            "code": code,
            "message": action,
        },
    }


def resolve_page_token(page_entry, token_vault, page_manager, *, operation="publish", refresh=False):
    """Resolve one exact discovery-backed mapping; never use a fallback token."""
    if not isinstance(page_entry, dict):
        return mapping_error("", "", "missing_page", detail="Invalid Page record in the selected target list.")
    page_entry = page_entry or {}
    page_id = str(page_entry.get("page_id") or "").strip()
    page_name = page_entry.get("page_name") or page_id
    token_id = str(page_entry.get("token_id") or "").strip()
    if operation not in ("publish", "comment", "read"):
        raise ValueError("Unsupported Meta preflight operation")
    if refresh and token_id:
        result = token_vault.ensure_page_access(token_id, page_manager)
        if not result.get("ok"):
            verdict = mapping_error(page_id, page_name, "page_access_refresh_failed", token_id=token_id,
                                    stage="page_access", detail=result.get("error", ""))
            verdict["action"] += " " + verdict["detail"]
            return verdict
    token_entry = token_vault.get_token_by_id(token_id) if token_id else None
    mapping, reason = page_manager.resolve_verified_mapping(page_id, token_entry)
    if reason == "missing_credential" and token_id:
        bindings = (page_entry.get("token_bindings") or {}).get(token_id)
        if bindings is not None and token_entry is not None:
            reason = "cross_bound_mapping"
    if reason:
        return mapping_error(page_id, page_name, reason, token_id=token_id)

    tasks = {str(task).upper() for task in (mapping.get("tasks") or [])}
    required_tasks = PUBLISH_TASKS if operation == "publish" else COMMENT_TASKS
    if operation != "read" and not tasks.intersection(required_tasks):
        return mapping_error(
            page_id,
            page_name,
            "publish_capability_missing" if operation == "publish" else "comment_capability_missing",
            stage=f"{operation}_capability",
            token_id=token_id,
            detail="Required Page task: CREATE_CONTENT." if operation == "publish" else "Required Page task: MODERATE.",
        )

    required_permissions = (REEL_REQUIRED_PERMISSIONS if operation == "publish" else
                            COMMENT_REQUIRED_PERMISSIONS if operation == "comment" else frozenset())
    permissions_status = token_entry.get("permissions_status", "unverified")
    missing = required_permissions - set(token_entry.get("granted_permissions") or [])
    if permissions_status == "verified" and missing:
        verdict = mapping_error(page_id, page_name, "permissions_missing", stage=f"{operation}_permissions",
                                token_id=token_id, detail="Missing scopes: " + ", ".join(sorted(missing)))
        verdict["action"] += " " + verdict["detail"]
        return verdict

    return {
        "ok": True,
        "page_id": page_id,
        "page_name": page_name,
        "token_id": mapping["token_id"],
        "token_name": mapping.get("token_name", ""),
        "token": mapping["page_token"],
        "verified_at": mapping.get("verified_at", ""),
        "credential_fingerprint": mapping.get("credential_fingerprint", ""),
        "tasks": sorted(tasks),
        "operation": operation,
        "required_permissions": sorted(required_permissions),
        "permissions_status": permissions_status,
        "stage": "ready",
        "code": "ok",
        "action": "",
        "reconnect_required": False,
    }


def preflight_pages(targets, token_vault, page_manager, *, operation="publish", refresh=False):
    """Validate all targets before any queue record is created."""
    ready = []
    for entry in targets:
        verdict = resolve_page_token(entry, token_vault, page_manager, operation=operation, refresh=refresh)
        if not verdict.get("ok"):
            return {"ok": False, "ready": ready, "blocked": verdict}
        ready.append(verdict)
    return {"ok": True, "ready": ready, "blocked": None}
