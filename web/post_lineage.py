"""Read-only links from recovery history to the actual replacement post."""

COMPLETED_REPLACEMENT_STATUSES = {"published", "success"}


def annotate_lineage(rows, all_posts):
    by_id = {str(row.get("id")): row for row in all_posts}
    for row in rows:
        target_id = row.get("replacement_post_id") or row.get("superseded_by")
        if row.get("status") != "superseded" or not target_id:
            continue
        target = by_id.get(str(target_id))
        row["replacement_post"] = ({key: target.get(key) for key in
            ("id", "title", "status", "page_id", "page_name", "token_id", "post_fb_id")} if target else None)
        row["replacement_reference"] = str(target_id)


def visible_posts(posts):
    """Hide superseded source rows after their replacement is actually posted.

    A replacement that is still queued, processing, failed, or missing remains
    visible so the operator can inspect or retry it. This is deliberately a
    read-only projection; the historical source row stays in ``posts.json``.
    """
    by_id = {str(row.get("id")): row for row in posts}
    result = []
    for row in posts:
        if row.get("status") != "superseded":
            result.append(row)
            continue
        target_id = row.get("replacement_post_id") or row.get("superseded_by")
        target = by_id.get(str(target_id)) if target_id else None
        if not target or str(target.get("status") or "").lower() not in COMPLETED_REPLACEMENT_STATUSES:
            result.append(row)
    return result
