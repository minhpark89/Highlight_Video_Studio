"""v1.3.0 regressions for the desktop shell, daily defaults, and Meta recovery."""
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import pytest

from src import output_pipeline as pipeline
from web import scheduled_publisher as worker
from web.meta_recovery import can_refresh_existing


def _group(times=("04:00", "10:50", "15:00")):
    return {
        "id": "g",
        "name": "NEW",
        "page_ids": ["p"],
        "schedule_config": {"times": list(times), "stagger_minutes": 15},
    }


def test_batch_daily_defaults_to_two_posts_when_group_has_three_times(tmp_path, monkeypatch):
    from web import app as api

    group = _group()
    monkeypatch.setattr(pipeline, "ROOT", tmp_path)
    monkeypatch.setattr(api.page_manager, "list_groups", lambda: [group])
    monkeypatch.setattr(api.page_manager, "list_pages", lambda: [{"page_id": "p"}])
    monkeypatch.setattr(api, "_ensure_recent_meta_health",
                        lambda: pytest.fail("daily-plan save must not call Meta"))

    response = api.app.test_client().post("/api/distribute/batch", json={
        "group_id": "g",
        "post_daily": True,
        "daily_slots": ["04:00", "10:50", "15:00"],
    })

    assert response.status_code == 200
    plan = response.get_json()["plan"]
    assert plan["posts_per_day"] == 2
    assert plan["slots"] == ["04:00", "10:50"]
    assert plan["group_schedule_times"] == ["04:00", "10:50", "15:00"]


def test_existing_upload_can_be_finished_with_meta_schedule_without_reupload(tmp_path, monkeypatch):
    row = {
        "id": "post",
        "status": "processing",
        "page_id": "9901",
        "token_id": "exact",
        "meta_upload_video_id": "9001",
        "scheduled_time": "2026-10-04 21:25:00",
        "title": "Original video highlight",
        "content": "Watch the source video for complete context.",
        "publish_mode": "app_queue",
    }
    seen = {
        "http_status": 200,
        "id": "9001",
        "video_status": "upload_complete",
        "uploading_status": "complete",
        "processing_status": "not_started",
        "publishing_status": "not_started",
        "copyright_matches": False,
        "error": "",
    }
    now = datetime(2026, 10, 5, 7)
    schedule_epoch = (now + timedelta(hours=2)).timestamp()
    path = tmp_path / "posts.json"
    monkeypatch.setattr(worker, "POSTS_FILE", path)
    poster = mock.Mock()
    poster.finish_existing_reel.return_value = {"accepted": True, "state": "accepted"}

    assert worker._resume_complete_upload(
        row, seen, poster, {"token": "fixture", "token_id": "exact"}, [row], now,
        force_retry=True, schedule_time=schedule_epoch,
    )

    poster.finish_existing_reel.assert_called_once()
    args, kwargs = poster.finish_existing_reel.call_args
    assert args[:3] == ("9901", "fixture", "9001")
    assert kwargs["token_id"] == "exact"
    assert kwargs["schedule_time"] == schedule_epoch
    assert row["publish_mode"] == "meta_scheduled"
    assert row["meta_scheduled_publish_time"] == schedule_epoch
    assert row["meta_schedule_status"] == "verification_pending"
    assert row["meta_upload_video_id"] == "9001"
    assert not poster.publish_reel.called
    assert json.loads(path.read_text(encoding="utf-8"))[0]["meta_upload_video_id"] == "9001"


@pytest.mark.parametrize("retry_stage", [
    "meta_processing", "meta_video_rejected", "meta_schedule_rejected", "facebook_publish",
])
def test_failed_existing_upload_is_refreshable_only_for_known_meta_retry_stages(retry_stage):
    base = {
        "status": "failed",
        "retry_stage": retry_stage,
        "meta_upload_video_id": "9001",
    }
    assert can_refresh_existing(base)
    assert not can_refresh_existing({**base, "outcome_unknown": True})
    assert not can_refresh_existing({**base, "retry_stage": "unknown"})


def test_desktop_recovery_choices_are_present_in_both_source_templates():
    root = Path(__file__).resolve().parents[1]
    index = (root / "web" / "index.html").read_text(encoding="utf-8")
    template = (root / "web" / "templates" / "index.html").read_text(encoding="utf-8")
    assert index == template
    assert "Đăng ngay bằng App" in index
    assert "Meta giữ lịch" in index
    assert "/recover-existing" in index
