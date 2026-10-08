"""Local queue views. Filter and paginate before any row enrichment."""
from collections import Counter
from web.dashboard import post_bucket

REVIEW_STATUSES = {"preparing", "draft"}


def queue_bucket(post):
    if post.get("video_recovery_stock_claim") and not post.get("page_id") and post.get("status") == "superseded":
        return "stock_used"
    if post.get("output_pipeline") and not post.get("page_id") and post.get("status") in REVIEW_STATUSES:
        return "stock"
    if post.get("status") in REVIEW_STATUSES:
        return post["status"]
    return post_bucket(post)


def select_posts(posts, *, view="posts", bucket="all", group_id="", page_id="", token_id="", page=1, page_size=50):
    if view not in ("posts", "review", "stock", "all"):
        raise ValueError("Unknown queue view")
    if not 1 <= page_size <= 100 or page < 1:
        raise ValueError("Page must be positive; page_size must be 1–100")
    scoped = []
    for post in posts:
        kind = queue_bucket(post)
        if view == "posts" and kind in ("stock", "stock_used", "preparing", "draft"):
            continue
        if view == "review" and (kind not in REVIEW_STATUSES or not post.get("page_id") or not post.get("token_id")):
            continue
        if view == "stock" and kind != "stock":
            continue
        if group_id and str(post.get("group_id") or "") != group_id:
            continue
        if page_id and str(post.get("page_id") or "") != page_id:
            continue
        if token_id and str(post.get("token_id") or "") != token_id:
            continue
        scoped.append(post)
    counts = dict(Counter(queue_bucket(p) for p in scoped))
    matching = [p for p in scoped if bucket == "all" or queue_bucket(p) == bucket
                or (bucket == "planned" and queue_bucket(p) in ("app", "sending", "meta"))
                or (bucket == "attention" and queue_bucket(p) in ("processing", "failed"))]
    matching.sort(key=lambda p: (str(p.get("created_at") or ""), str(p.get("scheduled_time") or ""), str(p.get("id") or "")), reverse=True)
    total = len(matching)
    page = min(page, max(1, (total + page_size - 1) // page_size))
    start = (page - 1) * page_size
    return {"items": matching[start:start + page_size], "total": total, "page": page,
            "page_size": page_size, "pages": max(1, (total + page_size - 1) // page_size),
            "counts": {"all": len(scoped), **counts}}


def group_summary(posts, groups, plans=()):
    counts = {}
    stock = 0
    for post in posts:
        bucket = queue_bucket(post)
        stock += bucket == "stock"
        gid = str(post.get("group_id") or "")
        counts.setdefault(gid, Counter())[bucket] += 1
    rows = []
    for group in groups:
        gid = str(group["id"])
        active = [p for p in plans if p.get("enabled") and p.get("daily") and gid in p.get("group_ids", [])]
        rows.append({"id": gid, "name": group.get("name") or gid, "counts": dict(counts.get(gid, {})),
                     "daily": bool(active), "plans": active})
    return {"groups": rows, "stock": stock, "ungrouped": dict(counts.get("", {}))}
