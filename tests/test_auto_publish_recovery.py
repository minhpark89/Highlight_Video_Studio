import json
from datetime import datetime, timedelta
from unittest import mock

import pytest

from web import scheduled_publisher as worker
from src.publisher.meta_reel_poster import MetaReelPoster


NOW = datetime(2026, 10, 5, 7)


def idle():
    return {"http_status": 200, "id": "9001", "video_status": "upload_complete",
            "uploading_status": "complete", "processing_status": "not_started",
            "publishing_status": "not_started", "copyright_matches": False, "error": ""}


def queued():
    return {"id": "post", "status": "processing", "page_id": "9901", "token_id": "exact",
            "meta_upload_video_id": "9001", "scheduled_time": "2026-10-04 21:25:00",
            "title": "Original video highlight", "content": "Watch the source video for complete context.",
            "publish_mode": "meta_scheduled", "meta_scheduled_publish_time": 1791123900}


def recover(row, seen=None, poster=None):
    return worker._resume_complete_upload(row, seen or idle(), poster or mock.Mock(),
        {"token": "fixture", "token_id": "exact"}, [row], NOW)


def test_idle_upload_is_finished_with_same_id_after_durable_marker(tmp_path, monkeypatch):
    row = queued()
    path = tmp_path / "posts.json"
    monkeypatch.setattr(worker, "POSTS_FILE", path)
    def finish(*args, **kwargs):
        persisted = json.loads(path.read_text())[0]
        assert persisted["auto_finish_state"] == "sending"
        assert persisted["meta_upload_video_id"] == "9001"
        assert args[:3] == ("9901", "fixture", "9001")
        assert "schedule_time" not in kwargs
        return {"accepted": True, "state": "accepted"}
    poster = mock.Mock()
    poster.finish_existing_reel.side_effect = finish
    assert recover(row, poster=poster)
    assert row["status"] == "processing" and row["auto_finish_state"] == "accepted"
    assert row["publish_mode"] == "app_queue"
    assert "meta_scheduled_publish_time" not in row
    assert not recover(row, poster=poster)
    assert poster.finish_existing_reel.call_count == 1
    poster.publish_reel.assert_not_called()


@pytest.mark.parametrize("changes", [
    {"http_status": 503}, {"id": "9002"}, {"error": "unavailable"},
    {"copyright_matches": True}, {"uploading_status": "in_progress"},
    {"processing_status": "in_progress"}, {"publishing_status": "published"},
    {"video_status": "processing"},
])
def test_uncertain_or_active_remote_state_never_receives_finish(changes):
    seen = {**idle(), **changes}
    poster = mock.Mock()
    assert not recover(queued(), seen, poster)
    poster.finish_existing_reel.assert_not_called()
    poster.publish_reel.assert_not_called()


def test_future_due_time_does_not_publish_early():
    row = queued()
    row["scheduled_time"] = "2026-10-05 08:00:00"
    poster = mock.Mock()
    assert not recover(row, poster=poster)
    poster.finish_existing_reel.assert_not_called()


def test_ambiguous_finish_needs_grace_and_two_fresh_idle_observations(tmp_path, monkeypatch):
    row = queued()
    monkeypatch.setattr(worker, "POSTS_FILE", tmp_path / "posts.json")
    poster = mock.Mock()
    poster.finish_existing_reel.side_effect = TimeoutError("fixture")
    assert recover(row, poster=poster)
    assert row["auto_finish_state"] == "unknown"
    assert not recover(row, poster=poster)
    row["auto_finish_started_at"] = (NOW - timedelta(seconds=1000)).strftime("%Y-%m-%d %H:%M:%S")
    row["auto_finish_idle_checks"] = 0
    assert not recover(row, poster=poster)
    assert recover(row, poster=poster)
    assert poster.finish_existing_reel.call_count == 2
    poster.publish_reel.assert_not_called()


def test_definitive_rejection_uses_backoff_and_preserves_upload(tmp_path, monkeypatch):
    row = queued()
    monkeypatch.setattr(worker, "POSTS_FILE", tmp_path / "posts.json")
    poster = mock.Mock()
    poster.finish_existing_reel.return_value = {"accepted": False, "state": "rejected", "error": "rate limit"}
    assert recover(row, poster=poster)
    assert row["auto_finish_retry_at"] == NOW.timestamp() + 30
    assert not recover(row, poster=poster)
    assert row["meta_upload_video_id"] == "9001"


def test_legacy_rejected_finish_recovers_automatically_on_the_existing_id(tmp_path, monkeypatch):
    row = queued()
    row.update(meta_finish_recovery_attempts=1, meta_finish_recovery_state="rejected",
               meta_finish_recovery_started_at="2026-10-05T06:30:00+07:00",
               meta_finish_recovery_error="Identity verification required")
    monkeypatch.setattr(worker, "POSTS_FILE", tmp_path / "posts.json")
    poster = mock.Mock()
    poster.finish_existing_reel.return_value = {"accepted": True, "state": "accepted"}
    assert recover(row, poster=poster)
    assert row["auto_finish_attempts"] == 2
    assert row["meta_finish_recovery_state"] == "rejected"
    assert poster.finish_existing_reel.call_args.args[:3] == ("9901", "fixture", "9001")
    poster.publish_reel.assert_not_called()


@pytest.mark.parametrize("error_field", ["auto_finish_error", "meta_finish_recovery_error"])
def test_identity_requirement_is_visible_until_meta_confirms_publication(error_field):
    from web.meta_diagnostics import diagnose
    row = {**queued(), error_field: "Identity verification required | code: 368 | subcode: 4854002"}
    assert diagnose(row, idle())["state"] == "identity_required"
    assert not diagnose(row, idle())["can_finish_existing"]
    assert diagnose(row, {**idle(), "publishing_status": "published"})["state"] == "published"


@pytest.mark.parametrize("legacy_state", ["requesting", "unknown", "accepted", None])
def test_legacy_uncertain_finish_requires_grace_and_two_idle_checks(tmp_path, monkeypatch, legacy_state):
    row = queued()
    row.update(meta_finish_recovery_attempts=1, meta_finish_recovery_state=legacy_state,
               meta_finish_recovery_started_at="2026-10-05T06:59:00+07:00")
    monkeypatch.setattr(worker, "POSTS_FILE", tmp_path / "posts.json")
    poster = mock.Mock()
    poster.finish_existing_reel.return_value = {"accepted": True, "state": "accepted"}
    assert not recover(row, poster=poster)
    poster.finish_existing_reel.assert_not_called()
    row = json.loads((tmp_path / "posts.json").read_text())[0]
    row["auto_finish_started_at"] = "2026-10-05T06:30:00+07:00"
    assert not recover(row, poster=poster)
    assert recover(row, poster=poster)
    assert poster.finish_existing_reel.call_count == 1
    assert row["auto_finish_attempts"] == 2
    poster.publish_reel.assert_not_called()


def test_only_local_safe_failures_are_requeued():
    safe = {"id": "safe", "status": "failed", "retryable": True, "retry_stage": "facebook_publish"}
    rows = [safe, {**safe, "id": "upload", "meta_upload_video_id": "9001"},
            {**safe, "id": "unknown", "outcome_unknown": True},
            {**safe, "id": "wait", "next_retry_at": NOW.timestamp() + 60},
            {**safe, "id": "manual", "retryable": False}]
    assert worker._requeue_safe_failures(rows, NOW.timestamp(), NOW)
    assert safe["status"] == "scheduled" and safe["publish_retry_attempts"] == 1
    assert all(r["status"] == "failed" for r in rows[1:])


def test_foreign_legacy_social_text_gets_english_fallback_without_provider():
    row = {"id": "legacy", "title": "Игра как жизнь", "content": "外国語の紹介です",
           "first_comment_snapshot": "外国語", "article_url": "https://example.test/story"}
    with mock.patch("src.content_packages.requests.post") as provider:
        assert worker._repair_non_english_post(row, [row])
    assert worker._post_public_text_is_english(row)
    assert row["legacy_source_title"] == "Игра как жизнь"
    assert row["first_comment"].count(row["article_url"]) == 1
    provider.assert_not_called()


def test_overdue_native_schedule_is_published_on_same_video(tmp_path, monkeypatch):
    row = queued()
    monkeypatch.setattr(worker, "POSTS_FILE", tmp_path / "posts.json")
    seen = {**idle(), "video_status": "ready", "processing_status": "complete", "publishing_status": "scheduled"}
    poster = mock.Mock()
    poster.publish_existing_scheduled_reel.return_value = {"accepted": True, "state": "accepted"}
    assert recover(row, seen, poster)
    poster.publish_existing_scheduled_reel.assert_called_once_with("9001", "fixture", "exact")
    poster.finish_existing_reel.assert_not_called()
    poster.publish_reel.assert_not_called()


def test_publish_existing_video_only_updates_existing_graph_id():
    response = mock.Mock(status_code=200, ok=True, headers={})
    response.json.return_value = {"success": True}
    with mock.patch("src.publisher.meta_reel_poster.requests.post", return_value=response) as write:
        result = MetaReelPoster().publish_existing_scheduled_reel("9001", "fixture", "exact")
    assert result["accepted"]
    assert write.call_args.args[0].endswith("/9001")
    assert write.call_args.kwargs["data"]["published"] == "true"


def test_transient_cms_failure_retries_only_its_linked_package():
    row = {"id": "cms", "status": "failed", "retryable": True, "retry_stage": "website_content",
           "content_package_id": "linked"}
    with mock.patch("src.content_packages.get_package", return_value={"id": "linked", "status": "failed", "website_error": "CMS HTTP 520"}), \
         mock.patch("src.content_packages.retry_package") as retry:
        assert worker._requeue_safe_failures([row], NOW.timestamp(), NOW)
    retry.assert_called_once_with("linked")


def test_definite_comment_failures_continue_after_eight_attempts(tmp_path, monkeypatch):
    from src.publisher import first_comment_queue as comments
    path = tmp_path / "comments.json"
    monkeypatch.setattr(comments, "QUEUE_FILE", path)
    path.write_text(json.dumps([{"id": "comment", "post_id": "post", "status": "pending", "due_at": 1,
                                "attempts": 8, "object_id": "9001", "page_token": "fixture", "comment_text": "Read the full article."}]))
    poster = mock.Mock()
    poster.post_first_comment.return_value = {"success": False, "error": "temporary quota"}
    comments.process_due_first_comments(poster, now=2)
    row = json.loads(path.read_text())[0]
    assert row["status"] == "pending" and row["attempts"] == 9
    assert row["due_at"] == 902
