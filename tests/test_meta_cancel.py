import json
from unittest import mock

import pytest
import requests

from src.publisher.meta_reel_poster import MetaReelPoster


class _Response:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload
        self.ok = 200 <= status < 400
        self.headers = {"x-fb-trace-id": "fixture-trace"}

    def json(self):
        return self._payload


def _scheduled(video="9001", page="9901"):
    return {"id": video, "from": {"id": page}, "status": {
        "video_status": "ready",
        "uploading_phase": {"status": "complete"},
        "processing_phase": {"status": "complete"},
        "publishing_phase": {"publish_status": "scheduled", "publish_time": 1791200000},
    }}


def test_delete_reel_requires_scheduled_and_verifies_remote_removal():
    poster = MetaReelPoster()
    get_results = iter([
        _Response(200, {"id": "9901"}),  # Page-token identity
        _Response(200, _scheduled()),
        _Response(400, {"error": {"code": 100, "error_subcode": 33, "message": "Unknown object"}}),
    ])
    with mock.patch("src.publisher.meta_reel_poster.requests.get", side_effect=lambda *a, **k: next(get_results)) as read, \
         mock.patch("src.publisher.meta_reel_poster.requests.delete", return_value=_Response(200, {"success": True})) as remove:
        result = poster.delete_reel("9001", "page-secret", "original", page_id="9901")
    assert result["success"] and result["safe_to_remove_local"] and result["state"] == "deleted"
    remove.assert_called_once()
    assert "page-secret" not in json.dumps(result)
    assert read.call_count == 3


def test_delete_reel_never_deletes_published_video():
    poster = MetaReelPoster()
    published = _scheduled()
    published["status"]["publishing_phase"] = {"publish_status": "published"}
    with mock.patch("src.publisher.meta_reel_poster.requests.get", side_effect=[
        _Response(200, {"id": "9901"}), _Response(200, published)
    ]), mock.patch("src.publisher.meta_reel_poster.requests.delete") as remove:
        result = poster.delete_reel("9001", "page-secret", "original", page_id="9901")
    assert not result["success"] and result["state"] == "unsafe"
    remove.assert_not_called()


def _api_fixture(tmp_path, monkeypatch):
    from web import app as api
    from src.publisher.page_manager import PageManager
    from src.publisher.token_vault import TokenVault

    vault = TokenVault(tmp_path)
    pages = PageManager(tmp_path)
    original = {"id": "original", "name": "Original", "token": "app-secret", "status": "ACTIVE"}
    current = {"id": "current", "name": "Current", "token": "other-secret", "status": "ACTIVE"}
    vault._save([original, current])
    pages.sync_pages_from_token(original, [{"id": "9901", "name": "Page", "access_token": "page-original", "tasks": ["CREATE_CONTENT"]}])
    pages.sync_pages_from_token(current, [{"id": "9901", "name": "Page", "access_token": "page-current", "tasks": ["CREATE_CONTENT"]}])
    pages.activate_bindings({"9901": "current"})
    path = tmp_path / "posts.json"
    row = {"id": "post-1", "status": "meta_scheduled", "page_id": "9901", "token_id": "original",
           "meta_video_id": "9001", "meta_upload_video_id": "9001", "first_comment_queue_id": "fc-1"}
    path.write_text(json.dumps([row]), encoding="utf-8")
    monkeypatch.setattr(api, "POSTS_FILE", path)
    monkeypatch.setattr(api, "token_vault", vault)
    monkeypatch.setattr(api, "page_manager", pages)
    return api, api.app.test_client(), path


def test_cancel_api_uses_original_binding_and_removes_local_only_after_meta_success(tmp_path, monkeypatch):
    api, client, path = _api_fixture(tmp_path, monkeypatch)
    seen = {}
    def cancel(video_id, page_token, token_id, **kwargs):
        seen.update(video_id=video_id, page_token=page_token, token_id=token_id, **kwargs)
        return {"success": True, "safe_to_remove_local": True, "state": "deleted"}
    monkeypatch.setattr(api.reel_poster, "delete_reel", cancel)
    with mock.patch("src.publisher.first_comment_queue.cancel_first_comment", return_value={"cancelled": 1}):
        response = client.post("/api/posts/post-1/cancel-meta", json={"confirm_cancel_meta": True, "video_id": "9001"})
    assert response.status_code == 200 and response.get_json()["local_removed"]
    assert {key: seen[key] for key in ("video_id", "page_token", "token_id", "page_id")} == {
        "video_id": "9001", "page_token": "page-original", "token_id": "original", "page_id": "9901"}
    assert json.loads(path.read_text()) == []


def test_cancel_batch_keeps_failed_remote_rows(tmp_path, monkeypatch):
    api, client, path = _api_fixture(tmp_path, monkeypatch)
    rows = json.loads(path.read_text())
    rows.append({**rows[0], "id": "post-2", "meta_video_id": "9002", "meta_upload_video_id": "9002"})
    path.write_text(json.dumps(rows), encoding="utf-8")
    monkeypatch.setattr(api.reel_poster, "delete_reel", lambda video_id, *args, **kwargs:
                        {"success": video_id == "9001", "safe_to_remove_local": video_id == "9001",
                         "state": "deleted" if video_id == "9001" else "rejected", "error": "fixture"})
    with mock.patch("src.publisher.first_comment_queue.cancel_first_comment", return_value={"cancelled": 0}):
        response = client.post("/api/posts/cancel-meta-batch", json={
            "confirm_cancel_meta": True, "post_ids": ["post-1", "post-2"],
            "video_ids": {"post-1": "9001", "post-2": "9002"}})
    data = response.get_json()
    assert response.status_code == 200 and data["succeeded"] == 1 and data["failed"] == 1
    assert [row["id"] for row in json.loads(path.read_text())] == ["post-2"]


@pytest.mark.parametrize("changes", [
    {"id": "9002"}, {"from": {"id": "9902"}}, {"from": {}},
    {"status": {}}, {"status": {"publishing_phase": {"publish_status": "processing"}}},
])
def test_wrong_object_owner_and_unknown_states_never_delete(changes):
    with mock.patch("src.publisher.meta_reel_poster.requests.get", side_effect=[
        _Response(200, {"id": "9901"}), _Response(200, {**_scheduled(), **changes})
    ]), mock.patch("src.publisher.meta_reel_poster.requests.delete") as remove:
        result = MetaReelPoster().delete_reel("9001", "page-secret", "original", page_id="9901")
    assert not result["success"]
    remove.assert_not_called()


@pytest.mark.parametrize("identity", [
    _Response(200, {"id": "9902"}), _Response(400, {"error": {"code": 190}}),
])
def test_wrong_page_token_identity_never_reads_or_deletes_video(identity):
    with mock.patch("src.publisher.meta_reel_poster.requests.get", return_value=identity) as read, \
         mock.patch("src.publisher.meta_reel_poster.requests.delete") as remove:
        result = MetaReelPoster().delete_reel("9001", "secret", "original", page_id="9901")
    assert result["state"] == "blocked" and read.call_count == 1
    remove.assert_not_called()


@pytest.mark.parametrize("video_response", [
    _Response(400, {"error": {"code": 100, "error_subcode": 33}}),
    _Response(500, {"error": {"code": 2}}), requests.Timeout("secret"),
])
def test_read_errors_cannot_mean_cancel_success(video_response):
    with mock.patch("src.publisher.meta_reel_poster.requests.get", side_effect=[
        _Response(200, {"id": "9901"}), video_response
    ]), mock.patch("src.publisher.meta_reel_poster.requests.delete") as remove:
        result = MetaReelPoster().delete_reel("9001", "secret", "original", page_id="9901")
    assert not result["success"] and "secret" not in json.dumps(result)
    remove.assert_not_called()


@pytest.mark.parametrize("delete_response", [
    _Response(400, {"error": {"code": 200, "error_subcode": 10, "message": "secret", "fbtrace_id": "trace"}}),
    _Response(200, {"success": False}), _Response(200, {}), _Response(500, {}), requests.Timeout("secret"),
])
def test_delete_rejection_or_unknown_never_authorizes_local_removal(delete_response):
    with mock.patch("src.publisher.meta_reel_poster.requests.get", side_effect=[
        _Response(200, {"id": "9901"}), _Response(200, _scheduled())
    ]), mock.patch("src.publisher.meta_reel_poster.requests.delete", side_effect=[delete_response]):
        result = MetaReelPoster().delete_reel("9001", "secret", "original", page_id="9901")
    assert not result["success"] and not result.get("safe_to_remove_local")
    assert "secret" not in json.dumps(result)


def test_saved_delete_receipt_resumes_read_only_after_followup_timeout():
    saved = []
    with mock.patch("src.publisher.meta_reel_poster.requests.get", side_effect=[
        _Response(200, {"id": "9901"}), _Response(200, _scheduled()), requests.Timeout("token")
    ]), mock.patch("src.publisher.meta_reel_poster.requests.delete", return_value=_Response(200, {"success": True})):
        first = MetaReelPoster().delete_reel("9001", "secret", "original", page_id="9901", on_delete_attempt=saved.append)
    assert first["state"] == "unknown" and saved[0]["state"] == "accepted"
    with mock.patch("src.publisher.meta_reel_poster.requests.get", side_effect=[
        _Response(200, {"id": "9901"}), _Response(400, {"error": {"code": 100, "error_subcode": 33}})
    ]), mock.patch("src.publisher.meta_reel_poster.requests.delete") as remove:
        second = MetaReelPoster().delete_reel("9001", "secret", "original", page_id="9901", confirmed_attempt=saved[0])
    assert second["success"]
    remove.assert_not_called()


@pytest.mark.parametrize("body", [{}, {"confirm_cancel_meta": True},
                                   {"confirm_cancel_meta": True, "video_id": "9002"}])
def test_api_requires_confirmation_and_exact_current_meta_id(tmp_path, monkeypatch, body):
    api, client, path = _api_fixture(tmp_path, monkeypatch)
    before = path.read_bytes()
    with mock.patch.object(api.reel_poster, "delete_reel") as remove:
        assert client.post("/api/posts/post-1/cancel-meta", json=body).status_code in (400, 409)
    remove.assert_not_called()
    assert before == path.read_bytes()


def test_api_keeps_failed_row_and_durable_cancel_intent(tmp_path, monkeypatch):
    api, client, path = _api_fixture(tmp_path, monkeypatch)
    with mock.patch.object(api.reel_poster, "delete_reel", return_value={"success": False, "state": "rejected",
             "attempt": {"http_status": 403, "error_code": 200}, "error": "page-original app-secret"}):
        response = client.post("/api/posts/post-1/cancel-meta", json={"confirm_cancel_meta": True, "video_id": "9001"})
    row = json.loads(path.read_text())[0]
    assert response.status_code == 409 and row["meta_cancel_requested"]
    assert row["meta_last_cancel_attempt"]["http_status"] == 403
    assert "page-original" not in response.get_data(as_text=True) and "app-secret" not in path.read_text()
    assert row["status"] == "meta_scheduled"


def test_local_cleanup_retry_does_not_delete_again(tmp_path, monkeypatch):
    api, client, path = _api_fixture(tmp_path, monkeypatch)
    with mock.patch.object(api.reel_poster, "delete_reel", return_value={"success": True, "safe_to_remove_local": True}), \
         mock.patch("src.publisher.first_comment_queue.cancel_first_comment", side_effect=OSError("secret")):
        response = client.post("/api/posts/post-1/cancel-meta", json={"confirm_cancel_meta": True, "video_id": "9001"})
    assert response.status_code == 409 and response.get_json()["meta_cancelled"]
    assert json.loads(path.read_text())[0]["meta_cancel_verified"]
    with mock.patch.object(api.reel_poster, "delete_reel") as remove, \
         mock.patch("src.publisher.first_comment_queue.cancel_first_comment", return_value={"cancelled": 1}):
        response = client.post("/api/posts/post-1/cancel-meta", json={"confirm_cancel_meta": True, "video_id": "9001"})
    assert response.status_code == 200 and json.loads(path.read_text()) == []
    remove.assert_not_called()
    assert len(json.loads((tmp_path / "data/meta_cancel_history.json").read_text())) == 1


def test_cancel_comment_queue_preserves_other_posts_and_prevents_emission(tmp_path, monkeypatch):
    from src.publisher import first_comment_queue as queue
    monkeypatch.setattr(queue, "QUEUE_FILE", tmp_path / "comments.json")
    for post_id in ("cancelled", "other"):
        queue.enqueue_first_comment("9001" if post_id == "cancelled" else "9002", "secret", "Read the full story",
                                    1, post_id=post_id)
    assert queue.cancel_first_comment(post_id="cancelled")["cancelled"] == 1
    assert queue.cancel_first_comment(post_id="cancelled")["cancelled"] == 0
    poster = mock.Mock()
    poster.post_first_comment.return_value = {"success": True, "comment_id": "comment"}
    queue.process_due_first_comments(poster, now=100)
    assert poster.post_first_comment.call_count == 1
    assert poster.post_first_comment.call_args.args[0] == "9002"


def test_cancellation_intent_disables_existing_publication_recovery(tmp_path):
    from web.meta_recovery import can_refresh_existing
    from web.scheduled_publisher import _resume_complete_upload
    from datetime import datetime
    post = {"id": "post", "status": "meta_scheduled", "meta_upload_video_id": "9001", "meta_cancel_requested": True}
    assert not can_refresh_existing(post)
    poster = mock.Mock()
    assert not _resume_complete_upload(post, {}, poster, {}, [post], datetime.now(), force_retry=True)
    assert not poster.mock_calls


def test_api_writes_intent_and_success_receipt_before_cleanup(tmp_path, monkeypatch):
    api, client, path = _api_fixture(tmp_path, monkeypatch)
    def remove(*args, **kwargs):
        assert json.loads(path.read_text())[0]["meta_cancel_requested"]
        receipt = {"state": "accepted", "video_id": "9001", "page_id": "9901", "token_id": "original"}
        kwargs["on_delete_attempt"](receipt)
        assert json.loads(path.read_text())[0]["meta_last_cancel_attempt"] == receipt
        return {"success": True, "safe_to_remove_local": True, "attempt": receipt}
    monkeypatch.setattr(api.reel_poster, "delete_reel", remove)
    with mock.patch("src.publisher.first_comment_queue.cancel_first_comment", return_value={"cancelled": 1}):
        response = client.post("/api/posts/post-1/cancel-meta", json={"confirm_cancel_meta": True, "video_id": "9001"})
    assert response.status_code == 200


@pytest.mark.parametrize("changes", [{"status": "published"}, {"token_id": "missing"}, {"token_id": ""}])
def test_unavailable_original_or_published_row_cannot_cancel(tmp_path, monkeypatch, changes):
    api, client, path = _api_fixture(tmp_path, monkeypatch)
    row = json.loads(path.read_text())[0]
    row.update(changes)
    path.write_text(json.dumps([row]), encoding="utf-8")
    with mock.patch.object(api.reel_poster, "delete_reel") as remove:
        response = client.post("/api/posts/post-1/cancel-meta", json={"confirm_cancel_meta": True, "video_id": "9001"})
    assert response.status_code == 409 and len(json.loads(path.read_text())) == 1
    remove.assert_not_called()


def test_existing_saved_page_token_can_cancel_when_old_binding_missing(tmp_path, monkeypatch):
    api, client, path = _api_fixture(tmp_path, monkeypatch)
    row = json.loads(path.read_text())[0]
    row["token"] = "saved-original"
    path.write_text(json.dumps([row]), encoding="utf-8")
    monkeypatch.setattr(api.page_manager, "resolve_verified_mapping", lambda *a: (None, "missing_mapping"))
    with mock.patch.object(api.reel_poster, "delete_reel", return_value={"success": False, "state": "blocked"}) as remove:
        response = client.post("/api/posts/post-1/cancel-meta", json={"confirm_cancel_meta": True, "video_id": "9001"})
    assert response.status_code == 409
    assert remove.call_args.args == ("9001", "saved-original", "original")
    assert "saved-original" not in response.get_data(as_text=True)


def test_save_failure_before_delete_never_calls_meta(tmp_path, monkeypatch):
    api, client, path = _api_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(api, "save_posts", mock.Mock(side_effect=OSError("secret")))
    with mock.patch.object(api.reel_poster, "delete_reel") as remove:
        response = client.post("/api/posts/post-1/cancel-meta", json={"confirm_cancel_meta": True, "video_id": "9001"})
    assert response.get_json()["code"] == "intent_save_failed"
    remove.assert_not_called()


def test_batch_failure_does_not_prevent_next_row_from_cleanup(tmp_path, monkeypatch):
    api, client, path = _api_fixture(tmp_path, monkeypatch)
    rows = json.loads(path.read_text())
    rows.append({**rows[0], "id": "post-2", "meta_video_id": "9002", "meta_upload_video_id": "9002"})
    path.write_text(json.dumps(rows), encoding="utf-8")
    monkeypatch.setattr(api.reel_poster, "delete_reel", lambda *a, **kw: {"success": True, "safe_to_remove_local": True})
    with mock.patch("src.publisher.first_comment_queue.cancel_first_comment", side_effect=[OSError("secret"), {"cancelled": 1}]):
        response = client.post("/api/posts/cancel-meta-batch", json={"confirm_cancel_meta": True,
            "post_ids": ["post-1", "post-2", "post-2"], "video_ids": {"post-1": "9001", "post-2": "9002"}})
    data = response.get_json()
    assert data["requested"] == 2 and data["succeeded"] == 1 and data["failed"] == 1
    assert [row["id"] for row in json.loads(path.read_text())] == ["post-1"]
    assert "secret" not in json.dumps(data)
