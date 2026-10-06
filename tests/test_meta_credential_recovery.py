import json
from datetime import datetime, timedelta
from unittest import mock

import pytest

from src.publisher.token_vault import TokenVault
from src.publisher.page_manager import PageManager
from web.meta_recovery import refresh_page_credential, can_retry_existing
from web import scheduled_publisher as worker


def idle(**changes):
    return {"id": "9001", "http_status": 200, "video_status": "upload_complete", "uploading_status": "complete",
            "processing_status": "not_started", "publishing_status": "not_started", "error": "", **changes}


@pytest.fixture
def recovery(tmp_path, monkeypatch):
    from web import app as api
    vault = TokenVault(tmp_path)
    pages = PageManager(tmp_path)
    entries = [{"id": tid, "name": tid, "token": tid+"-fixture", "status": "ACTIVE"} for tid in ("original", "alternative")]
    vault._save(entries)
    for entry in entries:
        pages.sync_pages_from_token(entry, [{"page_id": "9901", "page_name": "Page", "page_token": entry["id"]+"-cached",
                                           "tasks": ["CREATE_CONTENT"]}])
    path = tmp_path / "posts.json"
    row = {"id": "post", "page_id": "9901", "token_id": "original", "status": "processing",
           "meta_upload_video_id": "9001", "auto_finish_state": "rejected", "auto_finish_error": "368 / 4854002",
           "scheduled_time": "2026-10-04 21:00:00", "title": "Original video highlight",
           "content": "Watch the full video for more context.", "first_comment_snapshot": "Frozen comment"}
    path.write_text(json.dumps([row]), encoding="utf-8")
    for module in (api, worker):
        monkeypatch.setattr(module, "POSTS_FILE", path)
    monkeypatch.setattr(api, "token_vault", vault)
    monkeypatch.setattr(api, "page_manager", pages)
    monkeypatch.setattr(api.reel_poster, "inspect_reel", lambda *a: idle())
    monkeypatch.setattr(vault, "verify_token", lambda token: {"status": "ACTIVE", "pages": [
        {"page_id": "9901", "page_name": "Page", "page_token": "fresh-fixture", "tasks": ["CREATE_CONTENT"]}]})
    return api, api.app.test_client(), row, path, vault, pages


def test_refresh_replaces_stale_page_token_for_exact_original_credential(recovery):
    api, client, row, path, vault, pages = recovery
    credential, summary = refresh_page_credential(row, vault, pages)
    assert credential["token"] == "fresh-fixture" and credential["token_id"] == "original"
    assert summary["page_token_changed"]
    assert "fresh-fixture" not in json.dumps(summary)


@pytest.mark.parametrize("pages_result", [[], [{"page_id": "different", "page_token": "secret", "tasks": ["CREATE_CONTENT"]}],
    [{"page_id": "9901", "page_token": "secret", "tasks": ["ANALYZE"]}]])
def test_failed_or_wrong_page_refresh_preserves_cached_binding(recovery, monkeypatch, pages_result):
    api, client, row, path, vault, pages = recovery
    before = pages.pages_file.read_bytes()
    monkeypatch.setattr(vault, "verify_token", lambda token: {"status": "ACTIVE", "pages": pages_result})
    credential, summary = refresh_page_credential(row, vault, pages)
    assert credential is None and not summary["ok"]
    assert pages.pages_file.read_bytes() == before


@pytest.mark.parametrize("token_id", ["original", "alternative"])
def test_manual_recovery_uses_fresh_credential_preserves_original_and_fences_replay(recovery, token_id):
    api, client, row, path, vault, pages = recovery
    def finish(*args, **kwargs):
        saved = json.loads(path.read_text())[0]
        assert saved["auto_finish_state"] == "sending"
        assert saved["token_id"] == "original" and saved["meta_upload_video_id"] == "9001"
        assert args[:3] == ("9901", "fresh-fixture", "9001")
        assert kwargs["token_id"] == token_id
        return {"accepted": True, "state": "accepted"}
    body = {"confirm_existing_upload": True, "video_id": "9001", "token_id": token_id}
    with mock.patch.object(api.reel_poster, "finish_existing_reel", side_effect=finish) as write, \
         mock.patch.object(api.reel_poster, "publish_reel") as upload:
        response = client.post("/api/posts/post/recover-existing", json=body)
        assert response.status_code == 200 and response.get_json()["accepted"]
        assert client.post("/api/posts/post/recover-existing", json=body).status_code == 409
    assert write.call_count == 1
    upload.assert_not_called()
    saved = json.loads(path.read_text())[0]
    assert saved["first_comment_snapshot"] == row["first_comment_snapshot"]
    assert saved.get("meta_recovery_token_id", "original") == token_id


def test_scheduled_existing_object_is_published_without_reupload(recovery, monkeypatch):
    api, client, row, path, vault, pages = recovery
    seen = idle(video_status="ready", processing_status="complete", publishing_status="scheduled")
    monkeypatch.setattr(api.reel_poster, "inspect_reel", lambda *a: seen)
    with mock.patch.object(api.reel_poster, "publish_existing_scheduled_reel", return_value={"state": "accepted"}) as write, \
         mock.patch.object(api.reel_poster, "publish_reel") as upload:
        response = client.post("/api/posts/post/recover-existing", json={"confirm_existing_upload": True, "video_id": "9001"})
    assert response.status_code == 200 and response.get_json()["accepted"]
    write.assert_called_once_with("9001", "fresh-fixture", "original")
    upload.assert_not_called()


@pytest.mark.parametrize("changes", [{"id": "9002"}, {"http_status": 503}, {"copyright_matches": True},
    {"publishing_status": "published"}, {"processing_status": "in_progress"}])
def test_unsafe_observations_have_no_retry_action(changes):
    assert not can_retry_existing({"status": "processing", "meta_upload_video_id": "9001"}, idle(**changes))


def test_automatic_retry_refreshes_old_page_credential_before_same_id_write(recovery):
    api, client, row, path, vault, pages = recovery
    now = datetime.now()
    credential = {"token_id": "original", "token": "original-cached", "verified_at": "2020-01-01 00:00:00"}
    poster = mock.Mock()
    poster.inspect_reel.return_value = idle()
    poster.finish_existing_reel.return_value = {"state": "accepted"}
    assert worker._resume_complete_upload(row, idle(), poster, credential, [row], now, vault=vault, manager=pages)
    assert poster.finish_existing_reel.call_args.args[:3] == ("9901", "fresh-fixture", "9001")
    assert row["meta_credential_refresh"]["page_token_changed"]


def test_diagnosis_only_exposes_masked_credential_choices(recovery):
    api, client, row, path, vault, pages = recovery
    response = client.get("/api/posts/post/meta-diagnosis").get_json()
    assert response["diagnosis"]["can_retry_existing"]
    assert {p["token_id"] for p in response["recovery_credentials"]} == {"original", "alternative"}
    assert "fixture" not in json.dumps(response)


def test_refresh_can_recover_when_the_saved_binding_cannot_read_the_object(recovery, monkeypatch):
    api, client, row, path, vault, pages = recovery
    monkeypatch.setattr(api, "_inspect_post_meta", lambda post: ({"http_status": 403, "error": "Old token expired"}, None))
    assert client.get("/api/posts/post/meta-diagnosis").get_json()["diagnosis"]["can_retry_existing"]
    with mock.patch.object(api.reel_poster, "finish_existing_reel", return_value={"state": "accepted"}) as write:
        response = client.post("/api/posts/post/recover-existing", json={"confirm_existing_upload": True, "video_id": "9001"})
    assert response.status_code == 200
    assert write.call_args.args[:3] == ("9901", "fresh-fixture", "9001")


@pytest.mark.parametrize("status,tasks", [("UNVERIFIED", ["CREATE_CONTENT"]), ("VERIFIED", ["ANALYZE"])])
def test_manual_recovery_rejects_unverified_or_read_only_alternative(recovery, status, tasks):
    api, client, row, path, vault, pages = recovery
    saved = json.loads(pages.pages_file.read_text())
    saved[0]["token_bindings"]["alternative"].update(status=status, tasks=tasks)
    pages.pages_file.write_text(json.dumps(saved))
    with mock.patch.object(vault, "verify_token") as verify, mock.patch.object(api.reel_poster, "finish_existing_reel") as write:
        response = client.post("/api/posts/post/recover-existing", json={
            "confirm_existing_upload": True, "video_id": "9001", "token_id": "alternative"})
    assert response.status_code == 409
    verify.assert_not_called()
    write.assert_not_called()


def test_automatic_refresh_rechecks_remote_state_before_writing(recovery):
    api, client, row, path, vault, pages = recovery
    credential = {"token_id": "original", "token": "original-cached", "verified_at": "2020-01-01 00:00:00"}
    poster = mock.Mock()
    poster.inspect_reel.return_value = idle(publishing_status="published")
    assert not worker._resume_complete_upload(row, idle(), poster, credential, [row], datetime.now(), vault=vault, manager=pages)
    poster.finish_existing_reel.assert_not_called()
    poster.publish_existing_scheduled_reel.assert_not_called()


def test_read_only_refresh_recovers_binding_without_finish_upload_or_status_change(recovery, monkeypatch):
    api, client, row, path, vault, pages = recovery
    row.update(status='meta_scheduled', meta_scheduled_publish_time=datetime.now().timestamp() - 600)
    row.pop('auto_finish_error')
    path.write_text(json.dumps([row]))
    seen = idle(video_status='ready', processing_status='complete', publishing_status='scheduled')
    monkeypatch.setattr(api.reel_poster, 'inspect_reel', lambda *args: seen)
    with mock.patch.object(api.reel_poster, 'finish_existing_reel') as finish, \
         mock.patch.object(api.reel_poster, 'publish_reel') as upload, \
         mock.patch.object(api.reel_poster, 'publish_existing_scheduled_reel') as publish:
        response = client.post('/api/posts/post/refresh-meta', json={'token_id': 'alternative'})
    assert response.status_code == 200
    data = response.get_json()
    assert data['diagnosis']['state'] == 'schedule_overdue' and data['diagnosis']['can_sync_existing']
    assert 'fixture' not in json.dumps(data)
    saved = json.loads(path.read_text())[0]
    assert saved['status'] == 'meta_scheduled' and saved['meta_upload_video_id'] == '9001'
    assert saved['token_id'] == 'original' and saved['meta_recovery_token_id'] == 'alternative'
    assert saved['first_comment_snapshot'] == row['first_comment_snapshot']
    finish.assert_not_called()
    upload.assert_not_called()
    publish.assert_not_called()


def test_refresh_rejects_wrong_token_and_changed_remote_id(recovery, monkeypatch):
    api, client, row, path, vault, pages = recovery
    with mock.patch.object(vault, 'verify_token') as verify:
        assert client.post('/api/posts/post/refresh-meta', json={'token_id': 'unknown'}).status_code == 409
    verify.assert_not_called()
    def change_id(*args):
        row['meta_upload_video_id'] = 'new'
        path.write_text(json.dumps([row]))
        return idle()
    monkeypatch.setattr(api.reel_poster, 'inspect_reel', change_id)
    assert client.post('/api/posts/post/refresh-meta', json={}).status_code == 409
    assert 'meta_observation' not in json.loads(path.read_text())[0]
