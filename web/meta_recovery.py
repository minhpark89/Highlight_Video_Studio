"""Refresh an explicitly selected Page credential without changing upload IDs."""
from src.publisher.meta_preflight import PUBLISH_TASKS, preflight_pages
from web.meta_diagnostics import safe_error


def publishing_token_id(post):
    return str(post.get("meta_recovery_token_id") or post.get("token_id") or "")


def can_refresh_existing(post):
    state = post.get("auto_finish_state")
    if state is None and post.get("meta_finish_recovery_attempts"):
        state = post.get("meta_finish_recovery_state") or "unknown"
    return bool(not post.get("meta_cancel_requested") and post.get("status") in ("processing", "meta_scheduled") and post.get("meta_upload_video_id")
                and state not in ("sending", "accepted", "unknown", "requesting"))


def can_retry_existing(post, seen):
    idle = (seen.get("video_status") == "upload_complete" and seen.get("processing_status") == "not_started"
            and seen.get("publishing_status") == "not_started")
    scheduled = (seen.get("video_status") == "ready" and seen.get("processing_status") == "complete"
                 and seen.get("publishing_status") == "scheduled")
    return bool(can_refresh_existing(post)
        and str(seen.get("id")) == str(post["meta_upload_video_id"]) and seen.get("http_status") == 200
        and not seen.get("error") and not seen.get("copyright_matches") and seen.get("uploading_status") == "complete"
        and (idle or scheduled))


def refresh_page_credential(post, vault, manager, token_id=None):
    selected = str(token_id or publishing_token_id(post))
    entry = vault.get_token_by_id(selected)
    if not entry:
        return None, {"ok": False, "error": "Token không còn trong kho; hãy kết nối lại Token."}
    old, _ = manager.resolve_verified_mapping(post.get("page_id"), entry)
    result = vault.verify_token(entry.get("token") or "")
    if result.get("status") != "ACTIVE":
        return None, {"ok": False, "error": safe_error(result.get("error") or "Không đồng bộ được quyền Page.")}
    discovered = result.get("pages") or []
    target = next((p for p in discovered if str(p.get("page_id") or p.get("id")) == str(post.get("page_id"))), None)
    tasks = {str(task).upper() for task in (target or {}).get("tasks", [])}
    if not target or not tasks.intersection(PUBLISH_TASKS):
        return None, {"ok": False, "error": "Token được chọn chưa có quyền tạo nội dung trên đúng Page này."}
    page_token = target.get("page_token") or target.get("access_token")
    if not page_token:
        return None, {"ok": False, "error": "Meta chưa cấp Page token; hãy kết nối lại Token."}
    # A transient discovery failure must not invalidate the saved source token.
    active_entry = vault.record_verification(selected, entry.get("token") or "", result)
    if not active_entry:
        return None, {"ok": False, "error": "Credential thay đổi trong lúc Sync; hãy kiểm tra lại Token."}
    manager.sync_pages_from_token(active_entry, discovered, preserve_canonical=True)
    verdict = preflight_pages([{"page_id": str(post["page_id"]), "token_id": selected}], vault, manager)
    if not verdict.get("ok"):
        return None, {"ok": False, "error": (verdict.get("blocked") or {}).get("action") or "Mapping mới chưa hợp lệ; hãy kiểm tra Token trong kho."}
    return verdict["ready"][0], {"ok": True, "token_id": selected, "token_name": entry.get("name") or selected,
        "identity_valid": True, "page_access_verified": True, "tasks": sorted(tasks),
        "page_token_changed": bool(old and old.get("page_token") != page_token)}


def recovery_credentials(post, vault, manager):
    page = next((p for p in manager.list_pages() if str(p.get("page_id")) == str(post.get("page_id"))), {})
    tokens = {str(t.get("id")): t for t in vault.list_tokens(mask=True)}
    original = str(post.get("token_id") or "")
    ids = [original, *page.get("token_bindings", {})]
    options = []
    for tid in dict.fromkeys(ids):
        token = tokens.get(tid)
        if not token:
            continue
        binding = page.get("token_bindings", {}).get(tid) or {}
        tasks = {str(t).upper() for t in binding.get("tasks") or []}
        if tid != original and (token.get("status") != "ACTIVE" or binding.get("status") != "VERIFIED"
                                or not tasks.intersection(PUBLISH_TASKS)):
            continue
        options.append({"token_id": tid, "name": token.get("name") or tid,
                        "owner_name": token.get("owner_name") or "", "original": tid == original})
    return options
