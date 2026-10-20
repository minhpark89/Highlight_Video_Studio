"""Read existing objects in small batches, with one request per Token/Page."""
from concurrent.futures import ThreadPoolExecutor
import time

from src.publisher.meta_reel_poster import MetaReelPoster
from web.meta_recovery import publishing_token_id


def read_existing(post, page_manager, token_vault):
    from src.publisher.meta_preflight import preflight_pages
    token_id = publishing_token_id(post)
    exact_page = {"page_id": str(post.get("page_id") or ""), "token_id": token_id}
    verdict = preflight_pages([exact_page], token_vault, page_manager, operation="read")
    if not verdict.get("ok"):
        blocked = verdict.get("blocked") or {}
        return None, {"credential_error": blocked.get("action") or
                      "Mở Quản lý Token, đồng bộ quyền của đúng Page để tiếp tục."}
    credential = verdict["ready"][0]
    poster = MetaReelPoster(token_vault=token_vault)
    scheduled = post.get("publish_mode") == "meta_scheduled" or post.get("meta_scheduled_publish_time")
    candidates = (post.get("meta_upload_video_id"), post.get("meta_video_id"))
    if not any(candidates):
        candidates = (post.get("meta_post_id"),)
    check = {"verified": False}
    for candidate in dict.fromkeys(candidates):
        if not candidate:
            continue
        if scheduled:
            check = poster.check_scheduled_reel(
                candidate, credential["token"], post.get("meta_scheduled_publish_time"), token_id
            )
        else:
            check = poster.check_processing_reel(candidate, credential["token"], token_id)
        seen = check.get("meta_observation") or {}
        if check.get("verified") or (seen.get("id") == str(candidate) and seen.get("http_status") == 200):
            break
    return credential, check


def read_candidates(candidates, page_manager, token_vault, *, parallel=False, time_budget=20):
    """Only reads run in parallel; durable updates and recovery writes are serial."""
    started = time.monotonic()
    pending = list(candidates)
    examined = 0
    width = 4 if parallel else 1
    while pending:
        if examined and time.monotonic() - started >= time_budget:
            break
        batch = []
        tokens = set()
        pages = set()
        for post in pending:
            token_id = publishing_token_id(post)
            page_id = str(post.get("page_id") or "")
            if token_id in tokens or page_id in pages:
                continue
            batch.append(post)
            tokens.add(token_id)
            pages.add(page_id)
            if len(batch) == width:
                break
        for post in batch:
            pending.remove(post)
        if len(batch) == 1:
            results = [read_existing(batch[0], page_manager, token_vault)]
        else:
            with ThreadPoolExecutor(max_workers=len(batch), thread_name_prefix="meta-read") as executor:
                futures = [executor.submit(read_existing, post, page_manager, token_vault) for post in batch]
                results = []
                for future in futures:
                    try:
                        results.append(future.result())
                    except Exception:
                        results.append((None, {"credential_error": "Không đọc được Meta; app sẽ thử lại."}))
        for post, (credential, check) in zip(batch, results):
            examined += 1
            yield post, credential, check
