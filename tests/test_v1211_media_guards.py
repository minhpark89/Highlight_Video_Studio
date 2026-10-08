from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import json
import sys

import pytest

from src import job_store, long_transcription
from src.download_process import DownloadStalled, run_download
from src.media_quality_gate import clip_error, require_publishable
from web.post_lineage import annotate_lineage
from web.post_queries import select_posts
from web.queue_readiness import schedule_readiness


def test_download_stall_terminates_owned_process_and_keeps_partial(tmp_path):
    partial = tmp_path / "job.mp4.part"
    partial.write_bytes(b"resume-data")
    with pytest.raises(DownloadStalled):
        run_download([sys.executable, "-c", "import time; time.sleep(60)"],
                     tmp_path / "job.mp4", idle_timeout=0.3, maximum=3)
    assert partial.read_bytes() == b"resume-data"


def test_long_transcript_offsets_words_and_reuses_completed_chunks(tmp_path, monkeypatch):
    audio = tmp_path / "audio.mp3"
    audio.write_bytes(b"fixture")
    word = SimpleNamespace(word=" hello", start=1.25, end=1.5)
    segment = SimpleNamespace(start=1, end=2, text=" hello", words=[word])
    infer = mock.Mock(return_value=([segment], None))
    context = SimpleNamespace(TEMP_DIR=tmp_path, NO_WINDOW=0, _transcribe_whisper=infer,
                              get_whisper_model_source=lambda: "small")
    monkeypatch.setattr(long_transcription.subprocess, "run", lambda *a, **k:
                        SimpleNamespace(stdout=json.dumps({"format": {"duration": "601"}}), returncode=0))
    rows = long_transcription.transcribe(audio, context)
    assert [row["start"] for row in rows] == [1, 301, 601]
    assert rows[1]["words"][0]["start"] == 301.25
    assert infer.call_count == 3
    assert long_transcription.transcribe(audio, context) == rows
    assert infer.call_count == 3


def test_known_short_clip_is_blocked_without_affecting_unrelated_media(tmp_path):
    job_store.save(tmp_path / "jobs.json", [{"id": "old", "duration": 1153,
                                           "clips": [{"filename": "bad.mp4", "duration": 0.3}]}])
    bad = tmp_path / "output" / "bad.mp4"
    assert clip_error(bad)
    assert not clip_error(bad.with_name("good.mp4"))
    with pytest.raises(ValueError):
        require_publishable(bad)
    state = schedule_readiness({"status": "scheduled", "media_quality_error": clip_error(bad)}, {})
    assert state["blocked_code"] == "media_quality" and not state["actionable"]


def test_used_stock_is_hidden_and_old_post_points_to_real_replacement():
    replacement = {"id": "new", "status": "published", "page_id": "123", "page_name": "Correct Page"}
    old = {"id": "old", "status": "superseded", "replacement_post_id": "new"}
    stock = {"id": "stock", "status": "superseded", "video_recovery_stock_claim": True,
             "superseded_by": "new"}
    rows = [old, stock, replacement]
    annotate_lineage(rows, rows)
    assert old["replacement_post"]["page_id"] == "123"
    selected = select_posts(rows, bucket="other")
    assert [row["id"] for row in selected["items"]] == ["old"]


def test_retry_preserves_published_clip_removed_after_upload(tmp_path):
    from src.job_checkpoints import completed_clip, valid_plan
    output = tmp_path / "output"
    output.mkdir()
    clip = {"clip_index": 1, "filename": "already-posted.mp4", "start": 10, "end": 55}
    (tmp_path / "posts.json").write_text(json.dumps([
        {"id": "posted", "status": "published", "media_file": clip["filename"]}]))
    assert completed_clip({"clips": [clip]}, 1, clip, output) == clip
    assert valid_plan([clip], 1, 100)
    assert not valid_plan([{"start": 10, "end": 11}], 1, 100)
    with pytest.raises(ValueError):
        completed_clip({"clips": [clip]}, 1, {"start": 60, "end": 90}, output)
