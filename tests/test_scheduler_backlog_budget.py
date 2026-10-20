import json
from datetime import datetime
from unittest import mock

import pytest

from src.publisher import first_comment_queue as queue
from src.publisher.meta_reel_poster import MetaReelPoster
from src.publisher.page_manager import PageManager
from src.publisher.token_vault import TokenVault
from web import scheduled_publisher as worker
from web import meta_reconcile_reader as reader


@pytest.fixture
def isolated_queue(tmp_path, monkeypatch):
    monkeypatch.setattr(queue, "QUEUE_FILE", tmp_path / "comments.json")
    return queue.QUEUE_FILE


def add_comments(count=6):
    for index in reversed(range(count)):
        queue.enqueue_first_comment(str(index), "fixture", "Read story", 100 + index,
                                    post_id=f"post_{index}")


def test_oldest_readiness_checks_consume_budget_and_rotate(isolated_queue):
    add_comments()
    prepare = mock.Mock(return_value={"ready": False, "error": "Not published"})
    poster = mock.Mock()
    result = queue.process_due_first_comments(poster, now=200, prepare=prepare, max_items=2)
    assert result["examined"] == 2 and result["processed"] == 0
    assert [call.args[0]["object_id"] for call in prepare.call_args_list] == ["0", "1"]
    poster.post_first_comment.assert_not_called()
    prepare.reset_mock()
    queue.process_due_first_comments(poster, now=201, prepare=prepare, max_items=2)
    assert [call.args[0]["object_id"] for call in prepare.call_args_list] == ["2", "3"]
    rows = json.loads(isolated_queue.read_text())
    assert next(row for row in rows if row["object_id"] == "5")["due_at"] == 105


def test_soft_time_budget_saves_completed_request(isolated_queue):
    add_comments(3)
    poster = mock.Mock()
    poster.post_first_comment.return_value = {"success": True, "comment_id": "c0"}
    with mock.patch.object(queue.time, "monotonic", side_effect=[0, 21]):
        result = queue.process_due_first_comments(poster, now=200, time_budget_seconds=20)
    assert result["processed"] == result["examined"] == 1
    rows = json.loads(isolated_queue.read_text())
    first = next(row for row in rows if row["object_id"] == "0")
    assert first["status"] == "posted" and first["page_token"] == ""
    assert sum(row["status"] == "pending" for row in rows) == 2


@pytest.fixture
def isolated_scheduler(tmp_path, monkeypatch):
    for name, path in {
        "BASE_DIR": tmp_path, "POSTS_FILE": tmp_path / "posts.json",
        "OUTPUT_DIR": tmp_path / "output", "POSTED_CLIPS_FILE": tmp_path / "posted.json",
    }.items():
        monkeypatch.setattr(worker, name, path)
    monkeypatch.setattr(queue, "QUEUE_FILE", tmp_path / "comments.json")
    original = {"id": "tok_exact", "name": "Original", "token": "fixture", "status": "ACTIVE"}
    TokenVault(tmp_path)._save([original])
    PageManager(tmp_path).sync_pages_from_token(original, [
        {"id": "9901", "access_token": "page-original", "tasks": ["CREATE_CONTENT"]},
    ])
    now = datetime(2026, 10, 13, 14, 0)
    rows = [
        {"id": f"post_{index}", "status": "processing", "publish_mode": "meta_scheduled",
         "page_id": "9901", "token_id": "tok_exact", "meta_video_id": str(index),
         "meta_scheduled_publish_time": now.timestamp() - 600}
        for index in range(12)
    ]
    worker.POSTS_FILE.write_text(json.dumps(rows))
    return now, rows


def test_meta_batch_rotates_and_keeps_original_credential(isolated_scheduler):
    now, rows = isolated_scheduler
    with mock.patch.object(MetaReelPoster, "check_scheduled_reel", return_value={
        "verified": False, "status": "processing",
    }) as verify:
        worker._process_scheduled_posts_once(poster=mock.Mock(), now=now)
        assert verify.call_count == worker.META_RECONCILE_BATCH_SIZE
        assert all(call.args[1] == "page-original" for call in verify.call_args_list)
        verify.reset_mock()
        worker._process_scheduled_posts_once(poster=mock.Mock(), now=now)
        assert [call.args[0] for call in verify.call_args_list] == ["8", "9", "10", "11"]
    saved = json.loads(worker.POSTS_FILE.read_text())
    assert all(row["status"] == "processing" for row in saved)
    assert all(row["meta_next_check_at"] == now.timestamp() + 60 for row in saved)


def test_missing_credentials_backoff_allows_other_objects_next_cycle(isolated_scheduler):
    now, rows = isolated_scheduler
    for row in rows:
        row["token_id"] = "missing"
    worker.POSTS_FILE.write_text(json.dumps(rows))
    with mock.patch.object(MetaReelPoster, "check_scheduled_reel") as verify:
        worker._process_scheduled_posts_once(poster=mock.Mock(), now=now)
        first = json.loads(worker.POSTS_FILE.read_text())
        assert sum(bool(row.get("meta_next_check_at")) for row in first) == 8
        worker._process_scheduled_posts_once(poster=mock.Mock(), now=now)
        verify.assert_not_called()
    assert all(row["meta_next_check_at"] == now.timestamp() + 900
               for row in json.loads(worker.POSTS_FILE.read_text()))


def test_meta_time_budget_still_returns_after_one_slow_read(isolated_scheduler):
    now, rows = isolated_scheduler
    with mock.patch.object(MetaReelPoster, "check_scheduled_reel", return_value={
        "verified": False, "status": "processing",
    }) as verify, mock.patch.object(reader, "time", mock.Mock(wraps=reader.time)) as clock:
        clock.monotonic.side_effect = [0, 21]
        worker._process_scheduled_posts_once(poster=mock.Mock(), now=now)
    assert verify.call_count == 1
