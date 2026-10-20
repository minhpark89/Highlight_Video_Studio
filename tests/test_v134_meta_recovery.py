import copy
import json
import threading
from datetime import datetime
from unittest import mock

import pytest

from src.publisher.meta_reel_poster import MetaReelPoster
from src.publisher.page_manager import PageManager
from src.publisher.token_vault import TokenVault
from web import meta_reconcile_reader as reader
from web import scheduled_publisher as worker
from web.meta_reconcile_policy import due_candidates, queue_summary
from web.unknown_publish_recovery import attach_existing, return_to_draft, video_identifier


@pytest.fixture
def installation(tmp_path, monkeypatch):
    from src.publisher import first_comment_queue
    from web import app as api
    for module in (worker, api):
        monkeypatch.setattr(module, "POSTS_FILE", tmp_path / "posts.json")
        monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(worker, "BASE_DIR", tmp_path)
    monkeypatch.setattr(worker, "POSTED_CLIPS_FILE", tmp_path / "posted.json")
    monkeypatch.setattr(first_comment_queue, "QUEUE_FILE", tmp_path / "comments.json")
    vault = TokenVault(tmp_path)
    pages = PageManager(tmp_path)
    token = {"id": "original", "name": "Original", "token": "fixture", "status": "ACTIVE"}
    vault._save([token])
    pages.sync_pages_from_token(token, [{"id": "9901", "access_token": "page-original", "tasks": ["CREATE_CONTENT"]}])
    monkeypatch.setattr(api, "token_vault", vault)
    monkeypatch.setattr(api, "page_manager", pages)
    row = {"id": "broken", "status": "failed", "retry_stage": "publish_outcome_unknown",
           "outcome_unknown": True, "page_id": "9901", "token_id": "original",
           "scheduled_time": "2026-10-17 04:00:00", "publish_started_at": "2026-10-17 04:01:00",
           "title": "The original video", "content": "Watch the full story."}
    worker.POSTS_FILE.write_text(json.dumps([row]))
    return api, row


def test_failed_existing_upload_reconciles_while_upload_cycle_busy(installation):
    api, row = installation
    row["meta_upload_video_id"] = "9001"
    worker.POSTS_FILE.write_text(json.dumps([row]))
    with mock.patch.object(MetaReelPoster, "check_processing_reel", return_value={
        "verified": True, "video_id": "9001", "fb_url": "https://www.facebook.com/9901/videos/9001/",
    }), mock.patch.object(MetaReelPoster, "publish_reel") as upload, mock.patch.object(
            worker, "cleanup_published_clip_files",
            side_effect=AssertionError("Meta reconciliation must not wait for the disk cleanup worker")):
        assert worker._cycle_lock.acquire(blocking=False)
        try:
            result = worker.process_meta_maintenance_once(independent=True)
        finally:
            worker._cycle_lock.release()
    saved = json.loads(worker.POSTS_FILE.read_text())[0]
    assert result["reconciled"] == 1
    assert saved["status"] == "published" and saved["outcome_unknown"] is False
    assert saved["meta_upload_video_id"] == "9001"
    upload.assert_not_called()


def test_overdue_schedules_and_failed_rows_do_not_starve_old_processing():
    now = datetime(2026, 10, 20, 12).timestamp()
    old = [{"id": f"old-{i}", "status": "processing", "meta_video_id": str(i)} for i in range(400)]
    due = [{"id": f"due-{i}", "status": "meta_scheduled", "meta_video_id": str(1000 + i),
            "publish_mode": "meta_scheduled", "meta_scheduled_publish_time": now - 3600} for i in range(18)]
    failed = [{"id": f"failed-{i}", "status": "failed", "outcome_unknown": True,
               "meta_upload_video_id": str(2000 + i)} for i in range(10)]
    selected = due_candidates(old + due + failed, now)
    assert [sum(p["id"].startswith(prefix) for p in selected) for prefix in ("due", "failed", "old")] == [4, 2, 2]
    assert [sum(p["id"].startswith(prefix) for p in selected[:4]) for prefix in ("due", "failed", "old")] == [2, 1, 1]
    for row in selected:
        row["meta_next_check_at"] = now + 60
    following = due_candidates(old + due + failed, now)
    assert not {p["id"] for p in selected}.intersection(p["id"] for p in following)
    assert queue_summary(old + due + failed, now)["overdue_meta"] == 18


def test_parallel_reads_are_bounded_and_preserve_token_exclusion(monkeypatch):
    active = set()
    max_active = 0
    gate = threading.Barrier(4)
    lock = threading.Lock()
    def read(post, *_):
        nonlocal max_active
        with lock:
            assert post["token_id"] not in active
            active.add(post["token_id"])
            max_active = max(max_active, len(active))
        gate.wait(timeout=5)
        with lock:
            active.remove(post["token_id"])
        return {"token_id": post["token_id"]}, {"verified": False}
    monkeypatch.setattr(reader, "read_existing", read)
    rows = [{"id": str(i), "token_id": str(i % 4), "page_id": str(i)} for i in range(8)]
    results = list(reader.read_candidates(rows, None, None, parallel=True))
    assert len(results) == 8 and max_active == 4


def test_cancel_during_read_does_not_restore_old_state(installation):
    _, row = installation
    row.update(status="processing", meta_upload_video_id="9001")
    worker.POSTS_FILE.write_text(json.dumps([row]))
    def read(*_):
        current = worker.load_posts()
        current[0]["meta_cancel_requested"] = True
        worker.save_posts(current)
        return {"verified": True, "video_id": "9001"}
    with mock.patch.object(MetaReelPoster, "check_processing_reel", side_effect=read):
        worker.process_meta_maintenance_once(independent=True)
    saved = worker.load_posts()[0]
    assert saved["meta_cancel_requested"] and saved["status"] == "processing"


@pytest.mark.parametrize("url", ["/reel/9001/", "/9901/videos/9001/",
                                 "https://www.facebook.com/watch/?v=9001"])
def test_meta_confirmed_video_accepts_each_canonical_permalink(url):
    assert MetaReelPoster.public_video_permalink(url, "9001")


@pytest.mark.parametrize("url", ["https://facebook.com.evil.test/reel/9001/", "//evil.test/reel/9001/",
                                 "https://www.facebook.com/reel/9002/", "javascript:alert(1)"])
def test_permalink_cannot_confirm_a_different_video_or_host(url):
    assert not MetaReelPoster.public_video_permalink(url, "9001")


def test_missing_id_requires_explicit_review_and_keeps_history(installation):
    api, row = installation
    client = api.app.test_client()
    endpoint = "/api/posts/broken/resolve-unknown"
    assert client.post(endpoint, json={"action": "return_to_draft"}).status_code == 409
    assert worker.load_posts()[0]["outcome_unknown"] is True
    response = client.post(endpoint, json={"action": "return_to_draft", "confirmed_absent": True})
    assert response.status_code == 200, response.json
    saved = worker.load_posts()[0]
    assert saved["status"] == "draft" and saved["approval_mode"] == "manual"
    assert "publish_started_at" not in saved
    assert saved["publish_resolution_history"][0]["publish_started_at"] == row["publish_started_at"]
    assert client.post(endpoint, json={"action": "return_to_draft", "confirmed_absent": True}).status_code == 409


def test_link_existing_video_verifies_owner_and_fences_duplicates(installation):
    api, row = installation
    client = api.app.test_client()
    response = mock.Mock(ok=True)
    response.json.return_value = {"id": "9001", "from": {"id": "wrong-page"}}
    with mock.patch("web.unknown_publish_recovery.requests.get", return_value=response):
        rejected = client.post("/api/posts/broken/resolve-unknown", json={"action": "link_existing", "video_id": "9001"})
    assert rejected.status_code == 409
    assert "meta_upload_video_id" not in worker.load_posts()[0]
    response.json.return_value["from"]["id"] = "9901"
    with mock.patch("web.unknown_publish_recovery.requests.get", return_value=response):
        accepted = client.post("/api/posts/broken/resolve-unknown", json={"action": "link_existing", "video_id": "9001"})
    assert accepted.status_code == 200, accepted.json
    saved = worker.load_posts()[0]
    assert saved["status"] == "processing" and saved["meta_upload_video_id"] == "9001"
    with pytest.raises(ValueError, match="khác"):
        attach_existing(copy.deepcopy(row), [saved | {"id": "other"}], {"id": "9001"})


def test_no_remote_outcome_is_erased_by_a_draft_reset():
    row = {"status": "failed", "outcome_unknown": True, "meta_video_id": "9001"}
    with pytest.raises(ValueError):
        return_to_draft(row, True)
    assert row["outcome_unknown"] is True
    assert video_identifier("https://www.facebook.com/9901/videos/9001/") == "9001"
