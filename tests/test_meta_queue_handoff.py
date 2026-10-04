import copy
import json
import time
from datetime import datetime
from unittest import mock

import pytest

from web.meta_handoff import handoff_eligibility, process_next_handoff, queue_handoffs


@pytest.fixture
def queue_fixture(tmp_path, monkeypatch):
    from web import app as api
    from src.publisher.page_manager import PageManager
    from src.publisher.token_vault import TokenVault

    vault = TokenVault(tmp_path)
    pages = PageManager(tmp_path)
    credential = {"id": "tok_original", "name": "Fixture", "token": "fixture-token", "status": "ACTIVE"}
    vault._save([credential])
    pages.sync_pages_from_token(credential, [{"id": "9901", "name": "Page", "access_token": "fixture-page-token", "tasks": ["CREATE_CONTENT"]}])
    output = tmp_path / "output"
    output.mkdir()
    (output / "clip.mp4").write_bytes(b"video")
    post = {"id": "original", "status": "scheduled", "type": "reel", "media_file": "clip.mp4",
            "scheduled_time": datetime.fromtimestamp(int(time.time()) + 3600).strftime("%Y-%m-%d %H:%M:%S"),
            "page_id": "9901", "token_id": "tok_original", "title": "Original title", "content": "Original caption",
            "article_url": "https://example.test/story", "website_status": "ready",
            "first_comment": "Read https://example.test/story", "first_comment_snapshot": "Frozen https://example.test/story",
            "first_comment_source": "llm", "first_comment_profile_id": "frozen", "first_comment_model": "fixture"}
    posts_file = tmp_path / "posts.json"
    posts_file.write_text(json.dumps([post]), encoding="utf-8")
    for name, value in {"POSTS_FILE": posts_file, "OUTPUT_DIR": output, "token_vault": vault, "page_manager": pages}.items():
        monkeypatch.setattr(api, name, value)
    return api, api.app.test_client(), post, output, vault, pages, posts_file


def test_api_moves_original_row_without_upload_and_is_idempotent(queue_fixture):
    api, client, post, output, vault, pages, path = queue_fixture
    with mock.patch.object(api.reel_poster, "publish_reel") as upload:
        first = client.post("/api/posts/handoff-meta", json={"post_ids": ["original", "original"]})
        second = client.post("/api/posts/handoff-meta", json={"post_ids": ["original"]})
    assert first.get_json()["accepted_count"] == 1
    assert second.get_json()["accepted_count"] == 0
    upload.assert_not_called()
    saved = json.loads(path.read_text())
    assert len(saved) == 1 and saved[0]["id"] == post["id"]
    assert saved[0]["status"] == "meta_handoff"
    for field in ("scheduled_time", "token_id", "page_id", "title", "content", "first_comment_snapshot", "first_comment_profile_id", "first_comment_model"):
        assert saved[0][field] == post[field]


def test_api_reports_partial_selection_and_current_eligibility(queue_fixture):
    api, client, post, output, vault, pages, path = queue_fixture
    late = {**post, "id": "late", "scheduled_time": datetime.fromtimestamp(time.time() + 60).strftime("%Y-%m-%d %H:%M:%S")}
    path.write_text(json.dumps([post, late]))
    rows = client.get("/api/posts").get_json()
    assert next(row for row in rows if row["id"] == "original")["can_handoff_meta"]
    assert not next(row for row in rows if row["id"] == "late")["can_handoff_meta"]
    response = client.post("/api/posts/handoff-meta", json={"post_ids": ["original", "late", "missing"]})
    assert response.get_json()["accepted_count"] == 1 and response.get_json()["skipped_count"] == 2
    assert next(row for row in json.loads(path.read_text()) if row["id"] == "late")["status"] == "scheduled"


@pytest.mark.parametrize("changes", [{"meta_video_id": "9001"}, {"publish_started_at": "started"},
    {"outcome_unknown": True}, {"website_status": "failed"}, {"token_id": ""},
    {"first_comment_snapshot": "https://example.test/story https://example.test/story"}, {"status": "published"}])
def test_unsafe_rows_are_never_queued(queue_fixture, changes):
    api, client, post, output, vault, pages, path = queue_fixture
    row = {**post, **changes}
    assert not handoff_eligibility(row, output)[0]
    assert not queue_handoffs([row], [row["id"]], output, vault, pages)[0]["accepted"]


def test_credential_does_not_switch_to_later_page_default(queue_fixture):
    api, client, post, output, vault, pages, path = queue_fixture
    row = {**post, "token_id": "tok_missing_original"}
    assert not queue_handoffs([row], [row["id"]], output, vault, pages)[0]["accepted"]
    assert row["status"] == "scheduled" and row["token_id"] == "tok_missing_original"


def test_worker_persists_identity_and_consumes_frozen_comment(queue_fixture):
    api, client, post, output, vault, pages, path = queue_fixture
    rows = [copy.deepcopy(post)]
    queue_handoffs(rows, [post["id"]], output, vault, pages)
    revisions = []
    def save(rows):
        revisions.append(copy.deepcopy(rows))
    def publish(**kwargs):
        assert revisions[-1][0]["status"] == "processing"
        assert revisions[-1][0]["outcome_unknown"]
        assert kwargs["first_comment"] == post["first_comment_snapshot"]
        assert kwargs["token_id"] == "tok_original" and kwargs["post_id"] == "original"
        kwargs["on_upload_initialized"]("9001")
        assert revisions[-1][0]["meta_video_id"] == "9001"
        return {"success": True, "status": "SCHEDULED", "meta_video_id": "9001", "comment_result": {"success": True, "queue_id": "comment"}}
    poster = mock.Mock()
    poster.publish_reel.side_effect = publish
    assert process_next_handoff(rows, save, poster, output, vault, pages) == 1
    assert rows[0]["status"] == "meta_scheduled"
    assert rows[0]["first_comment_status"] == "pending"
    assert rows[0]["first_comment_snapshot"] == post["first_comment_snapshot"]
    process_next_handoff(rows, save, poster, output, vault, pages)
    assert poster.publish_reel.call_count == 1


def test_unknown_upload_never_returns_to_app_or_reuploads(queue_fixture):
    api, client, post, output, vault, pages, path = queue_fixture
    rows = [copy.deepcopy(post)]
    queue_handoffs(rows, [post["id"]], output, vault, pages)
    poster = mock.Mock()
    def uncertain(**kwargs):
        kwargs["on_upload_initialized"]("9001")
        return {"success": False, "outcome_unknown": True, "error": "fixture"}
    poster.publish_reel.side_effect = uncertain
    for _ in range(2):
        process_next_handoff(rows, lambda rows: None, poster, output, vault, pages)
    assert rows[0]["status"] == "processing" and rows[0]["meta_video_id"] == "9001"
    assert rows[0]["outcome_unknown"] and not rows[0]["retryable"]
    assert poster.publish_reel.call_count == 1


def test_expired_queue_returns_original_app_schedule_without_upload(queue_fixture):
    api, client, post, output, vault, pages, path = queue_fixture
    rows = [copy.deepcopy(post)]
    queue_handoffs(rows, [post["id"]], output, vault, pages)
    poster = mock.Mock()
    later = datetime.fromtimestamp(datetime.fromisoformat(post["scheduled_time"]).timestamp() - 600)
    process_next_handoff(rows, lambda rows: None, poster, output, vault, pages, now=later)
    assert rows[0]["status"] == "scheduled" and rows[0]["publish_mode"] == "app_queue"
    assert rows[0]["scheduled_time"] == post["scheduled_time"]
    assert rows[0]["meta_handoff_error"]
    poster.publish_reel.assert_not_called()


def test_preupload_rejection_preserves_original_schedule(queue_fixture):
    api, client, post, output, vault, pages, path = queue_fixture
    rows = [copy.deepcopy(post)]
    queue_handoffs(rows, [post["id"]], output, vault, pages)
    poster = mock.Mock()
    poster.publish_reel.return_value = {"success": False, "error": "Meta init rejected"}
    process_next_handoff(rows, lambda rows: None, poster, output, vault, pages)
    assert rows[0]["status"] == "scheduled" and not rows[0]["outcome_unknown"]
    assert not rows[0].get("meta_scheduled_publish_time")
    assert rows[0]["first_comment_snapshot"] == post["first_comment_snapshot"]


def test_transfer_does_not_race_active_worker_or_allow_local_delete(queue_fixture):
    from web.scheduled_publisher import _cycle_lock
    api, client, post, output, vault, pages, path = queue_fixture
    with _cycle_lock:
        response = client.post("/api/posts/handoff-meta", json={"post_ids": ["original"]})
    assert response.status_code == 409
    assert json.loads(path.read_text())[0]["status"] == "scheduled"
    client.post("/api/posts/handoff-meta", json={"post_ids": ["original"]})
    assert client.delete("/api/posts/original").status_code == 409
    assert client.post("/api/posts/clear", json={"status": "all"}).status_code == 409


def test_existing_worker_executes_queued_handoff(queue_fixture, monkeypatch, tmp_path):
    from web import scheduled_publisher as worker
    from src.publisher import first_comment_queue as comments
    api, client, post, output, vault, pages, path = queue_fixture
    client.post("/api/posts/handoff-meta", json={"post_ids": ["original"]})
    for name, value in {"BASE_DIR": tmp_path, "POSTS_FILE": path, "OUTPUT_DIR": output}.items():
        monkeypatch.setattr(worker, name, value)
    monkeypatch.setattr(comments, "QUEUE_FILE", tmp_path / "comments.json")
    poster = mock.Mock()
    poster.publish_reel.return_value = {"success": True, "status": "SCHEDULED", "meta_video_id": "9001", "comment_result": {"success": True}}
    result = worker.process_scheduled_posts_once(poster=poster)
    assert result["handed_off"] == 1 and not result["handoff_pending"]
    assert json.loads(path.read_text())[0]["status"] == "meta_scheduled"
    assert poster.publish_reel.call_count == 1
