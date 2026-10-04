"""Local overview statistics with an exhaustive, shared post classification."""
from collections import Counter
from datetime import datetime, timedelta
from web.meta_diagnostics import safe_error

BUCKETS = ("app", "sending", "publishing", "processing", "meta", "published", "failed", "other")


def post_bucket(post):
    status = str(post.get("status") or "").lower()
    if status in ("published", "success"):
        return "published"
    if status in ("failed", "error"):
        return "failed"
    if status == "scheduled":
        return "sending" if post.get("publish_mode") == "meta_scheduled" or post.get("requested_publish_mode") == "meta_scheduled" else "app"
    return {"meta_handoff": "sending", "meta_scheduled": "meta",
            "publishing": "publishing", "processing": "processing"}.get(status, "other")


def _day(value):
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value).date().isoformat()
        except (ValueError, OverflowError, OSError):
            return ""
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone().date().isoformat()
    except (ValueError, TypeError):
        return ""


def overview(posts, pages, tokens, groups, jobs, *, days=7, now=None):
    now = now or datetime.now()
    counts = dict.fromkeys(BUCKETS, 0)
    dates = [(now.date() - timedelta(days=days - 1 - i)).isoformat() for i in range(days)]
    series = {date: {"date": date, "published": 0, "scheduled": 0, "failed": 0} for date in dates}
    unknown_dates = 0
    attention = []
    for post in posts:
        bucket = post_bucket(post)
        counts[bucket] += 1
        field = "published" if bucket == "published" else "failed" if bucket == "failed" else "scheduled" if bucket in ("app", "sending", "meta") else None
        if field:
            date = _day(post.get("published_at") if field == "published" else
                        post.get("failed_at") or post.get("created_at") if field == "failed" else
                        post.get("meta_scheduled_publish_time") or post.get("scheduled_time"))
            if not date:
                unknown_dates += 1
            elif date in series:
                series[date][field] += 1
        if bucket in ("processing", "failed", "other"):
            attention.append({"id": post.get("id"), "title": post.get("title") or post.get("media_file") or "Bài chưa có tiêu đề",
                              "page_name": post.get("page_name") or post.get("page_id"), "bucket": bucket,
                              "meta_id": post.get("meta_upload_video_id") or post.get("meta_video_id") or post.get("meta_post_id"),
                              "diagnosis": post.get("meta_diagnosis") or {},
                              "error": safe_error(post.get("meta_publish_error") or post.get("error")),
                              "attempts": post.get("meta_reconcile_attempts") or 0})
    attention.sort(key=lambda post: (post["bucket"] != "processing", post["id"] or ""))
    return {"total_posts": len(posts), "post_counts": counts, "total_pages": len(pages),
            "total_tokens": len(tokens), "active_tokens": sum(t.get("status") == "ACTIVE" for t in tokens),
            "page_groups": len(groups), "scheduled_total": sum(counts[key] for key in ("app", "sending", "meta")),
            "comment_counts": dict(Counter(p.get("first_comment_status") or "not_configured" for p in posts)),
            "job_counts": dict(Counter(j.get("status") or "unknown" for j in jobs)),
            "series": list(series.values()), "unknown_chart_dates": unknown_dates,
            "attention": attention[:25], "attention_total": len(attention)}
