from datetime import datetime, timedelta
from unittest import mock
import copy
import pytest

from src import content_packages as packages
from src.video_recovery_media import file_digest, inventory
from tests.test_v127_media_and_cms import local, source_meta
from tests.test_v129_website_captions_recovery import ready_package
from tests.test_video_recovery import failed_post, FIXTURES
from web.posts_store import load_posts_file, save_posts_file
from web.queue_readiness import credential_block, schedule_readiness


def test_rejected_token_is_not_reported_as_cooldown_or_actionable():
    token = {"id": "original", "status": "ERROR", "error_msg": "[200] API access blocked."}
    post = {**failed_post(), "status": "scheduled"}
    result = schedule_readiness(post, {"original": token})
    assert result["blocked_code"] == "token_invalid" and not result["actionable"]
    assert "API access blocked" in result["blocked_reason"]
    assert result["action"] == "tokens"
    assert credential_block({"status": "ACTIVE", "rate_status": "COOLDOWN_80"})[0] == "token_cooldown"
    assert credential_block({"status": "ACTIVE"}) == ("", "")


def test_inventory_only_validates_language_of_selected_content(local, monkeypatch):
    _, directory, path = local
    (directory / "stock.mp4").write_bytes((FIXTURES / "tiny-video.mp4").read_bytes())
    item = ready_package("stock.mp4", file_digest(directory / "stock.mp4"))
    rows = [{**item, "id": f"unrelated-{index}", "clip_filename": f"absent-{index}.mp4",
             "source_sha256": f"different-{index}"} for index in range(1600)] + [item]
    monkeypatch.setattr(packages, "list_packages", lambda: rows)
    with mock.patch.object(packages, "package_is_english", wraps=packages.package_is_english) as language:
        result = inventory(directory, failed_post(), load_posts_file(path))
    assert result["candidates"][0]["ready_content"]
    assert language.call_count == 1


def test_background_recovery_accepts_before_slow_work_and_is_idempotent(local):
    api, directory, path = local
    from web import recovery_requests as tasks
    body = {"background": True, "mode": "app_queue"}
    with mock.patch.object(tasks.threading.Thread, "start") as start:
        first = api.app.test_client().post("/api/posts/bad/auto-recover", json=body)
        repeated = api.app.test_client().post("/api/posts/bad/auto-recover", json=body)
    assert first.status_code == repeated.status_code == 202
    assert first.get_json()["operation"]["id"] == repeated.get_json()["operation"]["id"]
    assert start.call_count == 1
    assert len(load_posts_file(path)) == 1
    changed = api.app.test_client().post("/api/posts/bad/auto-recover",
                                       json={**body, "filename": "other.mp4"})
    assert changed.status_code == 409
    with tasks._LOCK:
        tasks._ACTIVE.discard((str(directory.parent.resolve()), "bad"))


def test_persisted_request_resumes_and_keeps_busy_state_without_duplicate(local, monkeypatch):
    api, directory, path = local
    from web import recovery_requests as tasks
    (directory / "stock.mp4").write_bytes((FIXTURES / "tiny-video.mp4").read_bytes())
    ready_package("stock.mp4", file_digest(directory / "stock.mp4"))
    with mock.patch.object(tasks.threading.Thread, "start"):
        tasks.enqueue(directory.parent, "bad", {"mode": "app_queue"})
    original = api.api_auto_recover_failed_video
    attempts = []
    def busy_once(post_id, _body=None):
        attempts.append(post_id)
        if len(attempts) == 1:
            return api.jsonify({"success": False, "busy": True}), 409
        return original(post_id, _body=_body)
    monkeypatch.setattr(api, "api_auto_recover_failed_video", busy_once)
    monkeypatch.setattr(tasks.time, "sleep", lambda _: None)
    tasks._run(directory.parent.resolve(), "bad")
    operation = tasks.operation_for(directory.parent, "bad")
    assert operation["status"] == "complete" and len(attempts) == 2
    rows = load_posts_file(path)
    assert len(rows) == 2
    assert next(row for row in rows if row["id"] == "bad_replacement")["status"] == "scheduled"
    tasks._run(directory.parent.resolve(), "bad")
    assert len(load_posts_file(path)) == 2


def test_resume_pending_restarts_durable_request_once(local):
    api, directory, _ = local
    from web import recovery_requests as tasks
    root = directory.parent.resolve()
    with mock.patch.object(tasks.threading.Thread, "start") as start:
        operation = tasks.enqueue(root, "bad", {"mode": "app_queue"})
        tasks._ACTIVE.discard((str(root), "bad"))
        tasks.resume_pending(root)
        tasks.resume_pending(root)
    assert start.call_count == 2
    assert tasks.operation_for(root, "bad")["id"] == operation["id"]
    tasks._ACTIVE.discard((str(root), "bad"))


def test_changed_mp4_cannot_be_claimed_using_inventory_digest(local):
    _, directory, path = local
    from src import output_pipeline as pipeline
    from src.video_recovery_media import inventory_digest
    selected = directory / "stock.mp4"
    selected.write_bytes((FIXTURES / "tiny-video.mp4").read_bytes())
    digest = inventory_digest(selected)
    replacement = {"id": "replacement", "media_file": selected.name,
                   "replacement_video_sha256": digest, "source_sha256": digest}
    selected.write_bytes(selected.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="MP4"):
        pipeline.reserve_recovery(replacement, failed_post(), load_posts_file(path), directory.parent)
    assert len(load_posts_file(path)) == 1


def test_urgent_cycle_publishes_due_before_remote_maintenance(tmp_path):
    from web import scheduled_publisher as worker
    path = tmp_path / "posts.json"
    rows = [{"id": "due", "status": "scheduled", "page_id": "a", "token": "fixture",
             "scheduled_time": "2026-10-01 10:00:00"},
            {"id": "future", "status": "scheduled", "page_id": "b", "token": "other-fixture",
             "scheduled_time": "2026-10-02 10:00:00"},
            {"id": "remote", "status": "processing", "meta_video_id": "remote-video"}]
    save_posts_file(path, rows)

    def publish(post, *args):
        post["status"] = "published"
        return post

    poster = mock.Mock()
    with mock.patch.object(worker, "POSTS_FILE", path), \
         mock.patch("src.publisher.first_comment_queue.process_due_first_comments") as comments, \
         mock.patch("src.publisher.token_vault.TokenVault"), \
         mock.patch("src.publisher.page_manager.PageManager"), \
         mock.patch.object(worker, "_publish_claimed_post", side_effect=publish), \
         mock.patch.object(worker, "remove_posted_clip_file", return_value=False):
        result = worker.process_scheduled_posts_once(poster=poster, now=datetime(2026, 10, 1, 11), force_due=True)
    assert result["claimed"] == 1
    comments.assert_not_called()
    assert not poster.mock_calls
    saved = {post["id"]: post for post in load_posts_file(path)}
    assert saved["due"]["status"] == "published"
    assert saved["future"]["status"] == "scheduled"
    assert saved["remote"]["status"] == "processing"
