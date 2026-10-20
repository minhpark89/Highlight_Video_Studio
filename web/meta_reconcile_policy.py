"""Fair, bounded reconciliation for existing Meta objects."""
from datetime import datetime


REMOTE_FIELDS = ("meta_upload_video_id", "meta_video_id", "meta_post_id")
UNCERTAIN_STAGES = {
    "publish_outcome_unknown", "meta_processing", "meta_schedule_verification",
    "facebook_publish", "meta_schedule_rejected",
}


def timestamp(value):
    try:
        return float(value or 0)
    except (ValueError, TypeError):
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
        except (ValueError, TypeError, OverflowError):
            return 0


def existing_object(post):
    return next((str(post[key]) for key in REMOTE_FIELDS if post.get(key)), "")


def needs_reconciliation(post):
    if post.get("meta_cancel_requested") or post.get("local_archived_at"):
        return False
    if not existing_object(post):
        return False
    if post.get("status") in ("processing", "meta_scheduled"):
        return True
    return bool(post.get("status") == "failed" and (
        post.get("outcome_unknown") or post.get("retry_stage") in UNCERTAIN_STAGES
    ))


def native_due(post):
    if post.get("publish_mode") == "meta_scheduled" or post.get("meta_scheduled_publish_time"):
        return timestamp(post.get("meta_scheduled_publish_time") or post.get("scheduled_time"))
    return 0


def due_candidates(posts, now, limit=8):
    """Reserve turns for overdue schedules and uncertain failures, then rotate.

    Even a continual stream of overdue schedules leaves room for old processing
    records. A future schedule never consumes a verification turn before due.
    """
    eligible = []
    for post in posts:
        if not needs_reconciliation(post):
            continue
        due = native_due(post)
        if post.get("status") == "meta_scheduled" and due and now < due + 90:
            continue
        if timestamp(post.get("meta_next_check_at")) > now:
            continue
        eligible.append(post)
    eligible.sort(key=lambda post: timestamp(post.get("meta_next_check_at")))
    overdue = [post for post in eligible if native_due(post) and native_due(post) <= now - 90]
    overdue.sort(key=lambda post: post.get("status") != "meta_scheduled")
    uncertain = [post for post in eligible if post.get("status") == "failed"]
    selected = []
    selected_ids = set()
    lanes = []
    for lane, quota in ((overdue, max(1, limit // 2)), (uncertain, max(1, limit // 4)), (eligible, limit)):
        lane_selected = []
        taken = 0
        for post in lane:
            if len(selected) >= limit or taken >= quota:
                break
            if post.get("id") in selected_ids:
                continue
            selected.append(post)
            lane_selected.append(post)
            selected_ids.add(post.get("id"))
            taken += 1
        lanes.append(lane_selected)
    # A slow first wave can exhaust the network budget. Give every class a
    # place in that first wave instead of placing all failures after overdue.
    interleaved = []
    while any(lanes):
        for index in (0, 1, 2, 0):
            if lanes[index]:
                interleaved.append(lanes[index].pop(0))
    return interleaved


def next_delay(post, seen, now):
    """Stop repeatedly polling blocked credentials while due work is waiting."""
    if seen.get("error_code") in (10, 190, 200, 368):
        return 900
    if (post.get("meta_diagnosis") or {}).get("state") == "identity_required":
        return 1800
    if seen.get("http_status") not in (None, 200):
        return 120
    due = native_due(post)
    if due and now >= due:
        return 60
    if post.get("auto_finish_state") in ("sending", "accepted", "unknown"):
        return 60
    if post.get("status") == "failed" or int(post.get("meta_reconcile_attempts") or 0) < 5:
        return 60
    return 300


def queue_summary(posts, now):
    pending = [post for post in posts if needs_reconciliation(post)]
    overdue = [post for post in pending if native_due(post) and native_due(post) < now - 90]
    return {
        "pending": len(pending),
        "due": len(due_candidates(posts, now, limit=max(1, len(posts)))),
        "overdue_meta": len(overdue),
        "unknown_without_id": sum(
            post.get("status") == "failed" and not existing_object(post)
            and (post.get("outcome_unknown") or post.get("retry_stage") == "publish_outcome_unknown")
            and not post.get("local_archived_at") for post in posts
        ),
        "credential_blocked": sum(bool(post.get("meta_reconcile_error")) for post in pending),
    }
