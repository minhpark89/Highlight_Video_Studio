from datetime import datetime

from multi_pc.posting_schedule import paced_offsets_by_token, posting_schedule_recommendation, next_paced_due_post


def test_ten_lanes_spread_100_pages_over_about_150_minutes():
    rec = posting_schedule_recommendation(threads=10, pages=100, window_minutes=15)
    assert rec["seconds_between_lanes"] == 90.0
    assert rec["estimated_minutes"] == 148.5


def test_same_token_keeps_a_fifteen_minute_gap():
    offsets = paced_offsets_by_token(["a", "a", "b", "b"], global_seconds=90, token_seconds=900)
    assert offsets[1] - offsets[0] >= 900
    assert offsets[3] - offsets[2] >= 900


def test_backlog_releases_one_post_after_global_and_token_cooldowns():
    now = datetime(2026, 10, 3, 10, 1, 0)
    posts = [
        {"id": "done", "status": "published", "token_id": "a", "publish_started_at": "2026-10-03 10:00:00"},
        {"id": "a", "status": "scheduled", "token_id": "a", "scheduled_time": "2026-10-03 09:00:00"},
        {"id": "b", "status": "scheduled", "token_id": "b", "scheduled_time": "2026-10-03 09:01:00"},
    ]
    assert next_paced_due_post(posts, now) is None
    assert next_paced_due_post(posts, datetime(2026, 10, 3, 10, 2, 0))["id"] == "b"
    assert next_paced_due_post(posts, datetime(2026, 10, 3, 10, 15, 0))["id"] == "a"


def test_unprepared_website_does_not_starve_other_due_pages():
    now = datetime(2026, 10, 3, 10, 1, 0)
    posts = [
        {"id": "waiting", "status": "scheduled", "token_id": "a", "type": "reel",
         "scheduled_time": "2026-10-03 09:00:00", "website_status": "pending_generation"},
        {"id": "ready", "status": "scheduled", "token_id": "b", "type": "reel",
         "scheduled_time": "2026-10-03 09:01:00", "website_status": "ready",
         "article_url": "https://example.test/story", "first_comment": "https://example.test/story"},
    ]
    assert next_paced_due_post(posts, now)["id"] == "ready"
