"""Read-only display of original posting credentials and current assignments."""
from collections import Counter, defaultdict


def token_audit(posts, pages, tokens, groups=(), *, annotate_posts=None):
    catalog = {str(token.get("id")): token for token in tokens if token.get("id")}
    name_counts = Counter(str(token.get("name") or "") for token in catalog.values())
    page_map = {str(page.get("page_id")): page for page in pages if page.get("page_id")}
    group_map = {str(group.get("id")): group for group in groups if group.get("id")}
    by_token = defaultdict(list)
    configured_by_token = defaultdict(set)
    groups_by_token = defaultdict(set)
    allowed_by_group = {str(group.get("id")): {str(tid) for tid in group.get("token_ids", [])} for group in groups}
    for post in posts:
        if post.get("token_id"):
            by_token[str(post["token_id"])].append(post)
    for pid, page in page_map.items():
        configured_by_token[str(page.get("token_id") or "")].add(pid)
    for group in groups:
        allowed = allowed_by_group[str(group.get("id"))]
        for pid in group.get("page_ids", []):
            pid = str(pid)
            binding = str((group.get("page_token_bindings") or {}).get(pid) or page_map.get(pid, {}).get("token_id") or "")
            if not allowed or binding in allowed:
                groups_by_token[binding].add(pid)
    ids = set(catalog) | set(by_token)
    rows = []
    for token_id in sorted(ids):
        token = catalog.get(token_id, {})
        related = by_token[token_id]
        saved_name = next((post.get("token_name") for post in related if post.get("token_name") and
                           post.get("token_name") != "System User"), "")
        operator_name = str(token.get("name") or "")
        name = (token.get("owner_name") if name_counts[operator_name] > 1 and token.get("owner_name")
                else operator_name) or saved_name or ("Token đã xóa" if related else token_id)
        configured = configured_by_token[token_id]
        group_pages = groups_by_token[token_id]
        counts = Counter(str(post.get("status") or "unknown") for post in related)
        used = {str(post["page_id"]) for post in related if post.get("page_id")}
        rows.append({"token_id": token_id, "name": name, "owner_name": token.get("owner_name", ""),
                     "vault_present": bool(token), "configured_pages": len(configured),
                     "group_assigned_pages": len(group_pages), "posting_pages": len(used),
                     "posts": len(related), "published": counts["published"] + counts["success"],
                     "pending": sum(counts[status] for status in ("scheduled", "meta_scheduled", "processing", "publishing", "meta_handoff")),
                     "failed": counts["failed"],
                     "configured_page_ids": sorted(configured), "group_page_ids": sorted(group_pages),
                     "posting_page_ids": sorted(used)})
    lookup = {row["token_id"]: row for row in rows}
    for post in posts if annotate_posts is None else annotate_posts:
        token_id = str(post.get("token_id") or "")
        row = lookup.get(token_id, {})
        post["token_display_name"] = row.get("name") or "Chưa lưu Token ID"
        post["token_owner_name"] = row.get("owner_name", "")
        post["token_vault_present"] = row.get("vault_present", False)
        post["token_stats"] = {key: row.get(key, 0) for key in
                               ("configured_pages", "group_assigned_pages", "posting_pages", "posts", "published", "pending", "failed")}
        page = page_map.get(str(post.get("page_id") or ""), {})
        group = group_map.get(str(post.get("token_group_id") or ""))
        expected = ((group.get("page_token_bindings") or {}).get(str(post.get("page_id") or "")) or page.get("token_id")) if group else page.get("token_id")
        if group and group.get("token_ids") and str(expected or "") not in allowed_by_group[str(group.get("id"))]:
            expected = ""
        post["current_assigned_token_id"] = str(expected or "")
        post["token_assignment_match"] = (str(expected) == token_id) if expected and token_id else None
    return {"tokens": rows, "unknown_posts": sum(not post.get("token_id") for post in posts),
            "pages": [{"page_id": pid, "name": page.get("page_name") or pid} for pid, page in page_map.items()]}
