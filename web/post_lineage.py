"""Read-only links from recovery history to the actual replacement post."""


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
