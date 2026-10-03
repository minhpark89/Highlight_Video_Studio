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

    global_seconds = max(1, int(global_seconds))
    token_seconds = max(global_seconds, int(token_seconds))
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
