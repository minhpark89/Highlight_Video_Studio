"""Deterministic pacing recommendations for multi-Page publishing."""


def staggered_offset_seconds(index, *, threads=10, window_minutes=15, total=None):
    """Spread Pages across a bounded posting window instead of one burst."""
    index = max(0, int(index))
    threads = max(1, int(threads))
    window_seconds = max(60, int(window_minutes) * 60)
    if total is not None:
        threads = min(threads, max(1, int(total)))
    batch = index // threads
    lane = index % threads
    return int(round(batch * window_seconds + lane * (window_seconds / threads)))


def posting_schedule_recommendation(*, threads=10, pages=100, window_minutes=15):
    threads = max(1, int(threads))
    pages = max(1, int(pages))
    window_minutes = max(1, int(window_minutes))
    effective = min(threads, pages)
    total_seconds = staggered_offset_seconds(
        pages - 1, threads=effective, window_minutes=window_minutes, total=pages
    )
    return {
        "threads": effective,
        "pages": pages,
        "window_minutes": window_minutes,
        "seconds_between_lanes": round(window_minutes * 60 / effective, 1),
        "estimated_minutes": round(total_seconds / 60, 1),
    }


def paced_offsets_by_token(token_ids, *, global_seconds=90, token_seconds=900):
    """Assign offsets, allowing no burst and at least one token cooldown.

    The returned offsets correspond to the input order.  Pages are scheduled
    round robin across tokens when possible, preserving input order within each
    token.  This is an operational pacing policy, not a Meta rate-limit claim.
    """
    from collections import deque

    global_seconds = max(0, int(global_seconds))
    token_seconds = max(1, int(token_seconds))
    buckets = {}
    for index, token_id in enumerate(token_ids):
        buckets.setdefault(str(token_id), deque()).append(index)
    offsets = [0] * len(token_ids)
    next_token_time = {key: 0 for key in buckets}
    global_time = 0
    while buckets:
        chosen = min(buckets, key=lambda key: (max(global_time, next_token_time[key]), next_token_time[key], key))
        due = max(global_time, next_token_time[chosen])
        offsets[buckets[chosen].popleft()] = due
        global_time = due + global_seconds
        next_token_time[chosen] = due + token_seconds
        if not buckets[chosen]:
            del buckets[chosen]
    return offsets


def next_paced_due_post(posts, now, *, global_seconds=90, token_seconds=900):
    """Return one eligible due row; a backlog never becomes an upload burst."""
    from datetime import datetime, timedelta

    def parsed(value):
        try:
            stamp = datetime.fromisoformat(str(value))
            return stamp if stamp.tzinfo == now.tzinfo else None
        except (TypeError, ValueError):
            return None

    last_global = None
    last_by_token = {}
    due = []
    waiting = []
    for post in posts:
        if not isinstance(post, dict):
            continue
        started = parsed(post.get("publish_started_at"))
        if started is not None:
            last_global = max(last_global, started) if last_global else started
            token_id = str(post.get("token_id") or "")
            last_by_token[token_id] = max(last_by_token.get(token_id, started), started)
        scheduled = parsed(post.get("scheduled_time"))
        if post.get("status") == "scheduled" and scheduled is not None and scheduled <= now:
            if post.get("auto_first_comment") or post.get("type") == "reel":
                url = str(post.get("article_url") or "").strip()
                comment = str(post.get("first_comment") or "").strip()
                website_ready = post.get("website_status") in (None, "", "ready")
                if not (url and website_ready and url in comment):
                    waiting.append((scheduled, str(post.get("id") or ""), post))
                    continue
            due.append((scheduled, str(post.get("id") or ""), post))
    if global_seconds and last_global is not None and now - last_global < timedelta(seconds=global_seconds):
        return None
    for _, _, post in sorted(due, key=lambda item: (item[0], item[1])):
        previous = last_by_token.get(str(post.get("token_id") or ""))
        try:
            gap = max(1, int(post.get("token_gap_seconds") or token_seconds))
        except (TypeError, ValueError):
            gap = token_seconds
        if previous is None or now - previous >= timedelta(seconds=gap):
            return post
    # Preserve the old worker's diagnostic/status updates when there is no
    # publish-ready work; a waiting row must not starve a ready Page.
    if waiting:
        return min(waiting, key=lambda item: (item[0], item[1]))[2]
    return None
