import json
from datetime import datetime
from unittest import mock

import pytest
import requests

from web.dashboard import overview, post_bucket
from web.meta_diagnostics import diagnose, observation
from src.publisher.meta_reel_poster import MetaReelPoster


def pending_observation(**changes):
    seen = observation({"id": "9001", "status": {"video_status": "upload_complete",
                       "uploading_phase": {"status": "complete", "bytes_transferred": 100},
                       "processing_phase": {"status": "not_started"},
                       "publishing_phase": {"status": "not_started"}}}, 200)
    return {**seen, **changes}


def test_dashboard_accounts_for_the_missing_200th_post_and_unknown_states():
    rows = [{"id": str(i), "status": "published", "published_at": "2026-10-04 12:00:00"} for i in range(199)]
    rows.append({"id": "slow", "status": "processing", "meta_upload_video_id": "9001"})
    data = overview(rows, [], [], [], [], now=datetime(2026, 10, 4, 14))
    assert data["total_posts"] == sum(data["post_counts"].values()) == 200
    assert data["post_counts"]["processing"] == 1 and data["post_counts"]["published"] == 199
    assert data["attention"][0]["id"] == "slow"
    assert data["series"][-1]["published"] == 199
    data = overview(rows + [{"id": "new", "status": "future_state"}], [], [], [], [])
    assert data["post_counts"]["other"] == 1 and sum(data["post_counts"].values()) == 201


def test_dashboard_does_not_invent_dates_or_analytics():
    data = overview([{"status": "published"}], [], [], [], [])
    assert data["unknown_chart_dates"] == 1
    assert sum(row["published"] for row in data["series"]) == 0
    assert "followers" not in data and "reach" not in data


@pytest.mark.parametrize("status,bucket", [("scheduled", "app"), ("meta_handoff", "sending"),
    ("publishing", "publishing"), ("processing", "processing"), ("meta_scheduled", "meta"),
    ("published", "published"), ("success", "published"), ("failed", "failed"), ("cancelled", "other")])
def test_post_classification_is_exhaustive(status, bucket):
    assert post_bucket({"status": status}) == bucket


@pytest.fixture
def isolated_diagnostics(tmp_path, monkeypatch):
    from web import app as api
    from src.publisher.token_vault import TokenVault
    from src.publisher.page_manager import PageManager
    from web.posts_store import save_posts_file
    vault = TokenVault(tmp_path)
    manager = PageManager(tmp_path)
    entry = {"id": "tok_original", "name": "Original", "token": "original-fixture", "status": "ACTIVE"}
    vault._save([entry])
    manager.sync_pages_from_token(entry, [{"id": "9901", "name": "Page", "access_token": "page-fixture"}])
    path = tmp_path / "posts.json"
    post = {"id": "slow", "status": "processing", "meta_upload_video_id": "9001", "page_id": "9901",
            "token_id": "tok_original", "title": "Original title", "content": "Original caption",
            "first_comment_snapshot": "Frozen https://example.test/story", "scheduled_time": "2026-10-04 12:00:00"}
    save_posts_file(path, [post])
    for name, value in {"POSTS_FILE": path, "token_vault": vault, "page_manager": manager}.items():
        monkeypatch.setattr(api, name, value)
    monkeypatch.setattr(api.reel_poster, "inspect_reel", lambda *args: pending_observation())
    return api, api.app.test_client(), path, post, vault


def test_diagnosis_reports_observed_phases_and_historical_uncertainty(isolated_diagnostics):
    api, client, path, post, vault = isolated_diagnostics
    before = path.read_bytes()
    response = client.get("/api/posts/slow/meta-diagnosis").get_json()
    assert response["diagnosis"]["state"] == "finish_pending"
    assert response["diagnosis"]["can_finish_existing"]
    assert "không lưu" in response["diagnosis"]["detail"]
    assert path.read_bytes() == before  # The diagnostic GET does not rewrite the queue.
    assert "page-fixture" not in json.dumps(response)


def test_finish_claim_is_persisted_before_write_and_never_replayed(isolated_diagnostics):
    api, client, path, original, vault = isolated_diagnostics
    def finish(*args, **kwargs):
        saved = json.loads(path.read_text(encoding="utf-8"))[0]
        assert saved["meta_finish_recovery_attempts"] == 1 and saved["meta_finish_recovery_state"] == "requesting"
        assert args[2] == original["meta_upload_video_id"]
        return {"accepted": True, "state": "accepted", "error": ""}
    with mock.patch.object(api.reel_poster, "finish_existing_reel", side_effect=finish) as write:
        first = client.post("/api/posts/slow/finish-existing-upload", json={"confirm_existing_upload": True, "video_id": "9001"})
        second = client.post("/api/posts/slow/finish-existing-upload", json={"confirm_existing_upload": True, "video_id": "9001"})
    assert first.status_code == 200 and first.get_json()["accepted"]
    assert second.status_code == 409 and write.call_count == 1
    saved = json.loads(path.read_text(encoding="utf-8"))[0]
    for key, value in original.items():
        assert saved[key] == value
    assert saved["status"] == "processing"  # Acceptance cannot claim publication.


@pytest.mark.parametrize("changes", [{"publishing_status": "published"}, {"publishing_status": "scheduled"},
    {"processing_status": "processing"}, {"uploading_status": "in_progress"}, {"id": "different"},
    {"http_status": 400}, {"http_status": None}, {"error": "Graph error"}, {"copyright_matches": True}])
def test_changed_remote_state_prevents_finish(isolated_diagnostics, monkeypatch, changes):
    api, client, path, original, vault = isolated_diagnostics
    monkeypatch.setattr(api.reel_poster, "inspect_reel", lambda *args: pending_observation(**changes))
    with mock.patch.object(api.reel_poster, "finish_existing_reel") as write:
        response = client.post("/api/posts/slow/finish-existing-upload", json={"confirm_existing_upload": True, "video_id": "9001"})
    assert response.status_code == 409
    write.assert_not_called()


def test_cooldown_and_persistence_failure_cannot_send_finish(isolated_diagnostics, monkeypatch):
    api, client, path, original, vault = isolated_diagnostics
    entries = vault.list_tokens(mask=False)
    entries[0]["rate_status"] = "COOLDOWN_80"
    vault._save(entries)
    with mock.patch.object(api.reel_poster, "finish_existing_reel") as write:
        assert client.post("/api/posts/slow/finish-existing-upload", json={"confirm_existing_upload": True, "video_id": "9001"}).status_code == 409
        entries[0]["rate_status"] = "NORMAL"
        vault._save(entries)
        monkeypatch.setattr(api, "save_posts", mock.Mock(side_effect=OSError("fixture write failure")))
        assert client.post("/api/posts/slow/finish-existing-upload", json={"confirm_existing_upload": True, "video_id": "9001"}).status_code == 500
    write.assert_not_called()


def test_expired_native_schedule_does_not_silently_publish_now():
    post = {"status": "processing", "meta_upload_video_id": "9001", "token_id": "original",
            "publish_mode": "meta_scheduled", "scheduled_time": "2020-01-01 12:00:00"}
    assert not diagnose(post, pending_observation())["can_finish_existing"]


def test_finish_transport_sends_only_existing_id_and_unknown_outcome_is_not_success():
    response = mock.Mock(ok=True, status_code=200, headers={})
    response.json.return_value = {"success": True}
    with mock.patch("src.publisher.meta_reel_poster.requests.post", return_value=response) as write:
        result = MetaReelPoster().finish_existing_reel("9901", "fixture", "9001", "Original description")
    assert result["accepted"] and write.call_count == 1
    assert write.call_args.kwargs["data"]["upload_phase"] == "finish"
    assert write.call_args.kwargs["data"]["video_id"] == "9001"
    with mock.patch("src.publisher.meta_reel_poster.requests.post", side_effect=requests.Timeout()):
        result = MetaReelPoster().finish_existing_reel("9901", "fixture", "9001", "description")
    assert result["state"] == "unknown" and not result["accepted"]


def test_folder_browser_lists_directories_only_and_default_is_install_output(isolated_diagnostics, tmp_path, monkeypatch):
    api, client, path, original, vault = isolated_diagnostics
    output = tmp_path / "output"
    output.mkdir()
    (output / "source").mkdir()
    (output / "not-a-folder.mp4").write_text("fixture")
    monkeypatch.setattr(api, "OUTPUT_DIR", output)
    data = client.get("/api/folders").get_json()
    assert data["default_path"] == str(output)
    assert [item["name"] for item in data["directories"]] == ["source"]
    assert client.get("/api/folders", query_string={"path": str(output / "missing")}).status_code == 400
