import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from multi_pc.concurrency import RenderLimiter, saved_concurrency
from src import job_store


@pytest.fixture
def api(tmp_path, monkeypatch):
    from web import app
    monkeypatch.setattr(app, "IS_QUEUE_PAUSED", True)
    monkeypatch.setattr(app, "JOBS_FILE", tmp_path / "jobs.json")
    monkeypatch.setattr(app, "RENDER_QUEUE_STATE_FILE", tmp_path / "data" / "render_queue_state.json")
    monkeypatch.setattr(app, "AUTO_CONCURRENT_JOBS", 2)
    monkeypatch.setattr(app, "MAX_CONCURRENT_JOBS", 2)
    monkeypatch.setattr(app, "CONCURRENCY_MODE", "auto")
    return app


def test_manual_four_survives_state_reload_and_pause_changes(api):
    client = api.app.test_client()
    response = client.post("/api/queue/concurrency", json={"mode": "manual", "manual_concurrency": 4})
    assert response.status_code == 200
    assert response.json["concurrency"] == 4
    assert saved_concurrency(api.RENDER_QUEUE_STATE_FILE, 2) == ("manual", 4)
    api.set_render_queue_pause(True)
    assert saved_concurrency(api.RENDER_QUEUE_STATE_FILE, 2) == ("manual", 4)
    api.set_render_queue_pause(False)
    assert saved_concurrency(api.RENDER_QUEUE_STATE_FILE, 2) == ("manual", 4)
    assert client.get("/api/queue/status").json["max_concurrent"] == 4
    assert client.post("/api/queue/concurrency", json={"mode": "auto"}).json["concurrency"] == 2
    assert saved_concurrency(api.RENDER_QUEUE_STATE_FILE, 1) == ("auto", 1)


def test_failed_persistence_does_not_apply_unsaved_limit(api, monkeypatch):
    def fail(*args):
        raise PermissionError("fixture")
    monkeypatch.setattr(api, "_save_render_queue_state", fail)
    response = api.app.test_client().post("/api/queue/concurrency", json={"mode": "manual", "manual_concurrency": 4})
    assert response.status_code == 500
    assert api.CONCURRENCY_MODE == "auto"
    assert api.MAX_CONCURRENT_JOBS == 2


@pytest.mark.parametrize("payload", [{"mode":"manual", "manual_concurrency":5},
                                    {"mode":"manual", "manual_concurrency":0},
                                    {"mode":"manual", "manual_concurrency":2.5}])
def test_invalid_preferences_never_persist(api, payload):
    assert api.app.test_client().post("/api/queue/concurrency", json=payload).status_code == 400
    assert not api.RENDER_QUEUE_STATE_FILE.exists()


def test_resize_preserves_active_leases_and_wakes_waiting_render():
    limiter = RenderLimiter(1)
    entered = threading.Event()
    release = threading.Event()
    def work():
        with limiter.slot():
            entered.set()
            release.wait(3)
    with limiter.slot(), ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(work)
        try:
            assert not entered.wait(0.05)
            limiter.resize(2)
            assert entered.wait(1)
            limiter.resize(1)
            assert limiter.active == 2
            release.set()
            future.result(timeout=1)
            assert limiter.active == 1
        finally:
            release.set()
    assert limiter.active == 0


def test_large_jobs_query_is_bounded_searchable_and_counts_all_states(api):
    rows = [{"id": "job_" + str(i), "status": ["completed","queued","running","error"][i % 4],
             "created_at": "2026-10-11", "video_title": "Video " + str(i),
             "error": "encoder failed" if i % 4 == 3 else "",
             "all_segments": [{"text": "large transcript"}] * 100,
             "clips": [{"filename": "clip.mp4"}] * 3} for i in range(1264)]
    job_store.save(api.JOBS_FILE, rows)
    client = api.app.test_client()
    page = client.get("/api/jobs?status=error&page_size=25&page=2").json
    assert len(page["items"]) == 25
    assert page["page"] == 2 and page["pages"] == 13
    assert page["counts"] == {"completed":316, "queued":316, "running":316, "error":316, "total":1264}
    assert all(item["status"] == "error" and item["clip_count"] == 3 for item in page["items"])
    assert all("all_segments" not in item and "clips" not in item for item in page["items"])
    search = client.get("/api/jobs?status=error&q=encoder&page=999&page_size=100").json
    assert search["page"] == 4 and len(search["items"]) == 16
    assert client.get("/api/jobs?status=queued&q=encoder").json["items"] == []
    assert len(client.get("/api/jobs").json) == 1264
    assert client.get("/api/jobs/job_3").json["all_segments"] == rows[3]["all_segments"]


@pytest.mark.parametrize("query", ["page=0", "page=oops", "page_size=101", "page_size=0", "status=unknown"])
def test_job_page_rejects_invalid_bounds(api, query):
    assert api.app.test_client().get("/api/jobs?" + query).status_code == 400


def test_summary_reads_do_not_expose_mutable_snapshot(tmp_path):
    path = tmp_path / "jobs.json"
    job_store.save(path, [{"id":"one", "status":"queued", "clips":[{"file":"original"}]}])
    summary = job_store.page(path)
    summary["items"][0]["status"] = "error"
    one = job_store.get(path, "one")
    one["clips"][0]["file"] = "changed"
    assert job_store.get(path, "one")["clips"][0]["file"] == "original"
    assert job_store.counts(path)["queued"] == 1


def test_favicon_returns_actual_app_icon(api):
    root = Path(__file__).resolve().parents[1]
    response = api.app.test_client().get("/favicon.ico")
    assert response.status_code == 200
    assert response.data == (root / "assets" / "highlight.ico").read_bytes()


def test_existing_pipeline_limiter_receives_new_preference(api, monkeypatch):
    from src import pipeline
    monkeypatch.setattr(pipeline, "RENDER_LIMITER", RenderLimiter(2))
    monkeypatch.setattr(pipeline, "RENDER_CONCURRENCY", 2)
    api.app.test_client().post("/api/queue/concurrency", json={"mode":"manual", "manual_concurrency":4})
    assert pipeline.RENDER_CONCURRENCY == pipeline.RENDER_LIMITER.limit == 4


def test_dashboard_summary_never_copies_transcripts(api, monkeypatch):
    rows = [{"id":"one", "status":"running", "all_segments":[{"text":"large"}]*1000},
            {"id":"two", "status":"error", "clips":[{"filename":"unused"}]}]
    job_store.save(api.JOBS_FILE, rows)
    monkeypatch.setattr(api.page_manager, "list_pages", lambda: [])
    monkeypatch.setattr(api.page_manager, "list_groups", lambda: [])
    monkeypatch.setattr(api.page_manager, "mapping_health", lambda: {})
    monkeypatch.setattr(api.token_vault, "list_tokens", lambda **kwargs: [])
    monkeypatch.setattr(api.page_insights_service, "summary", lambda pages: {})
    monkeypatch.setattr(api, "read_posts_snapshot", lambda: [])
    def reject_full_ledger():
        raise AssertionError("Dashboard must only read status summaries")
    monkeypatch.setattr(api, "load_jobs", reject_full_ledger)
    response = api.app.test_client().get("/api/dashboard/summary")
    assert response.status_code == 200
    assert response.json["job_counts"] == {"running":1, "error":1}
    assert response.json["render"]["running"] == 1
    summary = job_store.status_rows(api.JOBS_FILE)
    assert all(set(row) == {"status"} for row in summary)
    summary[0]["status"] = "changed"
    assert job_store.get(api.JOBS_FILE, "one")["status"] == "running"
