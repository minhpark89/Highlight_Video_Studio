"""Preview and reserve today's Page schedules without reimporting videos."""
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import json

from src import output_pipeline as pipeline
from web.posts_store import load_posts_file, save_posts_file, _LOCK as POSTS_LOCK
from src.content_packages import _POST_SYNC_LOCK

REMOTE_FIELDS = ("meta_upload_video_id", "meta_video_id", "meta_post_id", "post_fb_id", "reel_id",
                 "outcome_unknown", "publish_started_at", "claimed_at", "meta_cancel_requested")


def _editable(post):
    return (post.get("output_pipeline") and post.get("status") in ("preparing", "draft")
            and not post.get("content_frozen_at") and not any(post.get(k) for k in REMOTE_FIELDS))


def _stamp(value):
    try:
        result = datetime.fromisoformat(str(value))
        return result.astimezone().replace(tzinfo=None) if result.tzinfo else result
    except (ValueError, TypeError):
        return None


def _bound_pages(group, pages, token_groups, plan):
    requested = str(plan.get("token_group_id") or "")
    token_group = next((g for g in token_groups if str(g.get("id")) == requested), None) if requested else next(
        (g for g in token_groups if str(g.get("page_group_id")) == str(group["id"])), None)
    if requested and not token_group:
        raise ValueError("Nhóm Token đã lưu không còn tồn tại; đồng bộ lại nhóm trước khi lên lịch")
    allowed = {str(pid) for pid in group.get("page_ids", [])}
    if token_group:
        allowed &= {str(pid) for pid in token_group.get("page_ids", [])}
    result = {}
    for original in pages:
        pid = str(original.get("page_id") or "")
        if pid not in allowed:
            continue
        token = str(original.get("token_id") or "")
        if token_group:
            token = str((token_group.get("page_token_bindings") or {}).get(pid) or token)
            if token not in {str(t) for t in token_group.get("token_ids", [])}:
                continue
        if token:
            result[pid] = {"page_id": pid, "page_name": original.get("page_name") or pid,
                           "token_id": token, "token_group_id": str(token_group["id"]) if token_group else "",
                           "group_id": str(group["id"]), "group_name": group.get("name") or str(group["id"])}
    return result


def schedule_today(options, pages, groups, token_groups=(), *, root=None, now=None):
    """Apply exactly the preview revision, retaining content and durable claims.

    Preparation continues in its saved approval mode. No CMS/Meta call is made;
    overflow keeps its original assignment rather than moving into tomorrow.
    """
    if not isinstance(options, dict):
        raise ValueError("Thiếu lựa chọn lên lịch hôm nay")
    root = Path(root or pipeline.ROOT)
    now = now or datetime.now()
    scope = options.get("scope", "selected")
    if scope not in ("selected", "group", "stock"):
        raise ValueError("Chọn bài đã tick, cả nhóm hoặc lấy thêm từ kho")
    group_id = str(options.get("group_id") or "")
    group = next((g for g in groups if str(g.get("id")) == group_id), None)
    if not group:
        raise ValueError("Chọn một nhóm Page để lên lịch hôm nay")
    mode = options.get("publish_mode", "meta_scheduled")
    approval = options.get("approval_mode", "preserve")
    if mode not in ("app_queue", "meta_scheduled") or approval not in ("preserve", "manual", "automatic"):
        raise ValueError("Chế độ lịch hoặc duyệt không hợp lệ")
    gap = options.get("interval_minutes", 15)
    if isinstance(gap, bool) or not isinstance(gap, int) or not 1 <= gap <= 1440:
        raise ValueError("Khoảng cách mỗi Token phải từ 1 đến 1440 phút")
    gap = timedelta(minutes=gap)
    apply = options.get("apply", False)
    if not isinstance(apply, bool):
        raise ValueError("apply phải là boolean")
    minimum = timedelta(minutes=20) if mode == "meta_scheduled" else timedelta(seconds=5)
    value = options.get("start_time")
    if value:
        try:
            start = datetime.combine(now.date(), datetime.strptime(str(value), "%H:%M").time())
        except ValueError as exc:
            raise ValueError("Giờ bắt đầu phải có dạng HH:MM") from exc
    else:
        start = (now + timedelta(minutes=30)).replace(second=0, microsecond=0) + timedelta(minutes=1)
    if start.date() != now.date() or start <= now + minimum:
        raise ValueError("Chọn giờ còn lại trong hôm nay, cách hiện tại hơn 20 phút cho Meta (5 giây cho App)")
    ids = options.get("post_ids", [])
    if scope == "selected" and (not isinstance(ids, list) or not 1 <= len(ids) <= 1000
                                or any(not isinstance(i, str) or not i for i in ids)):
        raise ValueError("Chọn từ 1 đến 1000 bài đang chuẩn bị hoặc Draft")
    count = options.get("stock_count", 100)
    if scope == "stock" and (isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 1000):
        raise ValueError("Số video lấy từ kho phải từ 1 đến 1000")
    with _POST_SYNC_LOCK, pipeline._LOCK, POSTS_LOCK, pipeline._connect(root) as db:
        # Finish a previously committed schedule after a failed JSON write.
        posts = load_posts_file(root / "posts.json")
        by_id = {p["id"]: p for p in posts}
        pending = list(db.execute("SELECT * FROM sources WHERE interface_written=0 AND intake!=''"))
        if pending:
            for source in pending:
                post = by_id.get(source["post_id"])
                if post and _editable(post):
                    post.update(json.loads(source["intake"]))
            save_posts_file(root / "posts.json", posts)
            db.execute("UPDATE sources SET interface_written=1 WHERE interface_written=0 AND intake!=''")
            db.commit()
        plans = pipeline.settings(root).get("plans", [])
        plan = next((p for p in plans if group_id in p.get("group_ids", [])), {})
        bound = _bound_pages(group, pages, token_groups, plan)
        if not bound:
            raise ValueError("Nhóm chưa có Page gắn đúng Token; đồng bộ Page/Token trước")
        if scope == "selected":
            candidates = [by_id.get(i, {"id": i}) for i in dict.fromkeys(ids)]
        else:
            candidates = [p for p in posts if _editable(p) and
                          (not p.get("page_id") if scope == "stock" else str(p.get("group_id")) == group_id)]
            candidates.sort(key=lambda p: (str(p.get("scheduled_time") or p.get("created_at") or ""), p["id"]))
            if scope == "stock":
                candidates = candidates[:count]
        sources = {s["sha256"]: s for s in db.execute("SELECT * FROM sources")}
        eligible, skipped = [], []
        for post in candidates:
            pid = str(post.get("page_id") or "")
            source = sources.get(post.get("source_sha256"))
            error = ""
            if not _editable(post):
                error = "Bài đã duyệt, đã giao Meta hoặc không còn ở phần chuẩn bị"
            elif not source or source["post_id"] != post["id"] or source["published"] or source["deleted_at"]:
                error = "Video không còn claim hợp lệ hoặc đã đăng"
            elif scope != "stock" and (str(post.get("group_id")) != group_id or pid not in bound):
                error = "Bài không thuộc nhóm Page đã chọn"
            elif scope != "stock" and (str(post.get("token_id")) != bound[pid]["token_id"] or
                                      str(post.get("token_group_id") or "") != bound[pid]["token_group_id"]):
                error = "Binding Page–Token đã thay đổi; đồng bộ và kiểm tra lại bài"
            if error:
                skipped.append({"post_id": post["id"], "error": error})
            else:
                eligible.append(post)
        def allocate(blocked):
            moving = {p["id"] for p in eligible if p["id"] not in blocked}
            token_times, page_times, page_load = {}, {}, {}
            def reserve(pid, tid, due, interval):
                token_times.setdefault(tid, []).append((due, interval))
                page_times.setdefault(pid, set()).add(due)
                if due.date() == now.date():
                    page_load[pid] = page_load.get(pid, 0) + 1
            for post in posts:
                if post["id"] in moving or post.get("status") not in pipeline.HELD_STATUSES:
                    continue
                due = _stamp(post.get("scheduled_time"))
                if due:
                    try:
                        previous_gap = timedelta(seconds=max(1, int(post.get("token_gap_seconds") or 900)))
                    except (TypeError, ValueError):
                        previous_gap = timedelta(minutes=15)
                    reserve(str(post.get("page_id") or ""), str(post.get("token_id") or ""), due, previous_gap)
            # Also honor ledger slots whose JSON interface is currently absent.
            moving_hashes = {p["source_sha256"] for p in eligible if p["id"] not in blocked}
            for slot in db.execute("SELECT * FROM slots"):
                if slot["sha256"] in moving_hashes:
                    continue
                due = _stamp(slot["scheduled_time"])
                assignment = json.loads(slot["assignment"])
                if due:
                    reserve(slot["page_id"], str(assignment.get("token_id") or ""), due, timedelta(minutes=15))
            end = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
            def next_time(binding):
                pid, tid = binding["page_id"], binding["token_id"]
                due = start
                for other, other_gap in sorted(token_times.get(tid, [])):
                    interval = max(gap, other_gap)
                    if other - interval < due < other + interval:
                        due = other + interval
                while due in page_times.get(pid, set()):
                    due += gap
                return due
            rows, updates, overflow = [], [], []
            for post in eligible:
                if post["id"] in blocked:
                    overflow.append({"post_id": post["id"], "error": "Hôm nay đã hết chỗ theo khoảng cách Token"})
                    continue
                if scope == "stock":
                    binding = min(bound.values(), key=lambda b: (next_time(b) >= end, page_load.get(b["page_id"], 0), next_time(b), b["page_id"]))
                else:
                    binding = bound[str(post["page_id"])]
                due = next_time(binding)
                if due >= end:
                    overflow.append({"post_id": post["id"], "error": "Hôm nay đã hết chỗ theo khoảng cách Token"})
                    # Overflow keeps its old slot, which remaining rows must honor.
                    old = _stamp(post.get("scheduled_time"))
                    if old:
                        reserve(str(post.get("page_id") or ""), str(post.get("token_id") or ""), old, gap)
                    continue
                review_mode = approval if approval != "preserve" else post.get("approval_mode") or plan.get("approval_mode") or "manual"
                assignment = {**binding, "scheduled_time": due.strftime("%Y-%m-%d %H:%M:%S"),
                              "requested_publish_mode": mode, "approval_mode": review_mode,
                              "token_gap_seconds": int(gap.total_seconds()), "schedule_day": now.date().isoformat(),
                              "schedule_assigned_at": now.isoformat(timespec="seconds"), "schedule_origin": "today",
                              "schedule_scope": scope}
                updates.append((post, assignment))
                rows.append({"post_id": post["id"], "status": post["status"], "previous_time": post.get("scheduled_time", ""),
                             **{k: v for k, v in assignment.items() if k != "schedule_assigned_at"}})
                reserve(binding["page_id"], binding["token_id"], due, gap)
            return rows, updates, overflow

        # A row that does not fit keeps its original slot. Replan with that
        # reservation so earlier moves cannot occupy an overflow row's slot.
        blocked = set()
        while True:
            rows, updates, overflow = allocate(blocked)
            next_blocked = blocked | {r["post_id"] for r in overflow}
            if next_blocked == blocked:
                break
            blocked = next_blocked
        # Fingerprint excludes the changing clock, but includes exact proposed
        # rows and claim identities. Recompute under the same locks at apply.
        revision = hashlib.sha256(json.dumps({"date": now.date().isoformat(), "scope": scope,
            "rows": rows, "skipped": skipped, "overflow": overflow,
            "hashes": [p["source_sha256"] for p, _ in updates]}, sort_keys=True).encode()).hexdigest()
        if apply and options.get("revision") != revision:
            raise ValueError("Danh sách hoặc lịch đã thay đổi; xem trước lại trước khi áp dụng")
        if apply and updates:
            for post, _ in updates:
                db.execute("DELETE FROM slots WHERE sha256=?", (post["source_sha256"],))
            for post, assignment in updates:
                post.update(assignment)
                post.pop("schedule_error", None)
                db.execute("INSERT INTO slots VALUES(?,?,?,?,?)", (post["page_id"], post["scheduled_time"],
                           post["source_sha256"], post.get("daily_plan_id") or "today", json.dumps(assignment)))
                # A schedule edit must not mark content as manually edited:
                # the pending worker still needs to fill its First Comment.
                snapshot = {k: v for k, v in post.items() if k not in ("token", "page_token", "access_token")}
                db.execute("UPDATE sources SET assigned=1,intake=?,interface_written=0 WHERE sha256=?",
                           (json.dumps(snapshot), post["source_sha256"]))
            db.commit()
            save_posts_file(root / "posts.json", posts)
            for post, _ in updates:
                db.execute("UPDATE sources SET interface_written=1 WHERE sha256=?", (post["source_sha256"],))
            if scope in ("group", "stock"):
                cfg = pipeline.settings(root)
                for daily in cfg.get("plans", []):
                    if group_id in daily.get("group_ids", []):
                        daily["allocation_override_date"] = now.date().isoformat()
                pipeline._write(root / "config/output_pipeline.json", cfg)
        return {"date": now.date().isoformat(), "server_now": now.isoformat(timespec="seconds"),
                "start_time": start.strftime("%H:%M"), "revision": revision, "applied": apply,
                "count": len(rows), "requested": len(candidates), "items": rows,
                "overflow": overflow, "skipped": skipped,
                "first_time": min((r["scheduled_time"] for r in rows), default=""),
                "last_time": max((r["scheduled_time"] for r in rows), default=""),
                "automatic": sum(r["approval_mode"] == "automatic" for r in rows)}
