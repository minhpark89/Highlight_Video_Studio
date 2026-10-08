from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import json
import os

import pytest

from multi_pc.json_io import shared_reader, replace_with_retry
from src import job_store, pipeline
from src.render_quality import seconds, validate_render


@pytest.mark.skipif(os.name != "nt", reason="Windows delete sharing")
def test_windows_reader_cannot_turn_a_job_update_into_render_failure(tmp_path):
    target = tmp_path / "jobs.json"
    job_store.save(target, [{"id": "job", "step": 1}])
    with shared_reader(target), mock.patch.object(job_store.threading.Thread, "start"):
        assert job_store.save(target, [{"id": "job", "step": 2}])
        assert job_store.load(target)[0]["step"] == 2
    assert job_store.flush(target)
    assert json.loads(target.read_text())[0]["step"] == 2


def test_locked_job_file_keeps_updates_durable_and_flushes_after_restart(tmp_path):
    path = tmp_path / "jobs.json"
    job_store.save(path, [{"id": "a", "step": 0}, {"id": "b", "step": 0}])
    with mock.patch.object(job_store, "replace_with_retry", side_effect=PermissionError("locked")), \
         mock.patch.object(job_store.threading.Thread, "start"):
        for index in range(2):
            rows = job_store.load(path)
            rows[index]["step"] = index + 1
            assert job_store.save(path, rows)
    job_store._CACHE.clear()
    assert [row["step"] for row in job_store.load(path)] == [1, 2]
    assert job_store.flush(path)
    assert [row["step"] for row in json.loads(path.read_text())] == [1, 2]
    assert not list(tmp_path.glob("*.tmp"))


def test_corrupt_jobs_never_become_an_empty_queue(tmp_path):
    path = tmp_path / "jobs.json"
    path.write_text("[broken")
    with pytest.raises(ValueError):
        job_store.load(path)


def test_short_llm_timecodes_are_replaced_by_usable_highlights():
    bad = [{"start": 13.08, "end": 14.12}, {"start": 15.46, "end": 16.48},
           {"start": 18.24, "end": 18.57}]
    result = pipeline._ensure_highlight_count(bad, [], 3, video_duration=1153)
    assert len(result) == 3
    assert all(30 <= item["end"] - item["start"] <= 75 for item in result)
    assert seconds("13:08") == 788
    assert seconds("1:13:08") == 4388


def test_complete_cached_download_survives_prior_network_timeout(tmp_path, monkeypatch):
    from src import media_download as downloader
    (tmp_path / "downloads").mkdir()
    (tmp_path / "temp").mkdir()
    path = tmp_path / "downloads" / "job.mp4"
    path.write_bytes(b"fixture")
    job_store.save(tmp_path / "jobs.json", [{"id": "job", "youtube_url": "https://youtu.be/source",
                                           "video_title": "Known title", "duration": 5396}])
    context = SimpleNamespace(DOWNLOADS_DIR=path.parent, TEMP_DIR=tmp_path / "temp")
    monkeypatch.setattr(downloader, "_complete", lambda *args: {"duration": 5396})
    with mock.patch.object(downloader, "_download_attempts") as network, \
         mock.patch.object(downloader, "_audio"):
        result = downloader.download(context, "https://youtu.be/source", "job")
    network.assert_not_called()
    assert result["title"] == "Known title" and result["duration"] == 5396


def test_render_quality_rejects_short_video_behind_long_audio(monkeypatch):
    from src import render_quality as quality
    monkeypatch.setattr(quality, "probe_video", lambda *a, **k: {"duration": 55})
    result = SimpleNamespace(stdout=json.dumps({"streams": [{"duration": "1.0",
                             "avg_frame_rate": "30/1", "nb_frames": "30"}]}))
    monkeypatch.setattr(quality.subprocess, "run", lambda *a, **k: result)
    with pytest.raises(ValueError, match="Luồng hình"):
        validate_render(Path("fixture.mp4"), 55, decode=False)


def test_failed_token_sync_preserves_last_verified_name(tmp_path, monkeypatch):
    from src.publisher.token_vault import TokenVault
    vault = TokenVault(tmp_path)
    vault._save([{"id": "same", "token": "fixture", "name": "Test 2", "owner_name": "Autopost 24"}])
    monkeypatch.setattr(vault, "verify_token", lambda _: {"status": "ERROR", "owner_name": "",
                                                        "error": "API access blocked", "identity_valid": False})
    entry, _ = vault.refresh_token_pages("same")
    assert entry["owner_name"] == "Autopost 24" and entry["status"] == "ERROR"
