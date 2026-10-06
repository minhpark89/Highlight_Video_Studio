import copy
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from unittest import mock

import pytest

from src.media_validation import InvalidMedia, probe_video
from src.publisher.meta_reel_poster import MetaReelPoster
from web.meta_diagnostics import observation
from web.video_recovery import can_replace_failed_video, prepare_replacement


FIXTURES = Path(__file__).parent / "fixtures"


def rejected_seen(**changes):
    value = observation({"id": "9001", "status": {"video_status": "error",
        "uploading_phase": {"status": "complete", "bytes_transferred": 262},
        "processing_phase": {"status": "complete"}, "publishing_phase": {"status": "not_started"},
        "copyright_check_status": {"matches_found": False}}}, 200)
    return {**value, **changes}


def failed_post():
    return {"id": "bad", "status": "processing", "type": "reel", "page_id": "9901", "token_id": "original",
        "title": "Original launch trailer", "content": "Watch the original launch trailer.",
        "media_file": "broken.mp4", "meta_upload_video_id": "9001", "meta_post_id": "9901_9001",
        "article_url": "https://example.test/blog/story", "website_status": "ready",
        "website_embed_status": "ready", "first_comment": "Watch https://example.test/blog/story",
        "first_comment_snapshot": "Watch https://example.test/blog/story", "outcome_unknown": True}


def test_empty_262_byte_mp4_is_blocked_before_any_meta_call(tmp_path):
    path = tmp_path / "broken.mp4"
    path.write_bytes((FIXTURES / "empty-video.mp4").read_bytes())
    assert path.stat().st_size == 262
    with mock.patch("src.publisher.meta_reel_poster.requests.post") as write:
        result = MetaReelPoster().publish_reel("9901", "fixture", path, description="Original launch trailer")
    assert result["code"] == "invalid_media" and not result["success"] and not result["retryable"]
    assert not result["outcome_unknown"]
    write.assert_not_called()


def test_probe_requires_real_video_and_fails_closed_without_ffprobe(tmp_path):
    path = tmp_path / "clip.mp4"
    path.write_bytes((FIXTURES / "tiny-video.mp4").read_bytes())
    assert probe_video(path)["duration"] > 0
    with mock.patch("src.media_validation.subprocess.run", side_effect=FileNotFoundError()):
        with pytest.raises(InvalidMedia):
            probe_video(path)


def test_llm_timestamps_past_source_end_are_reselected_within_real_duration():
    from src import pipeline
    response = mock.Mock()
    response.json.return_value = {"choices": [{"message": {"content": json.dumps([
        {"start_time": 120, "end_time": 175}, {"start_time": 210, "end_time": 268},
        {"start_time": 300, "end_time": 360}])}}]}
    with mock.patch.object(pipeline.requests, "post", return_value=response):
        clips = pipeline.ask_llm_for_highlights([], num_clips=3, video_duration=129.613787)
    assert len(clips) == 3
    assert all(0 <= c["start"] < c["end"] <= 129.613787 for c in clips)
    assert not any(c["start"] == 210 for c in clips)


def test_render_past_eof_stops_before_transcoding_and_preserves_existing_output(tmp_path):
    from src import pipeline
    output = tmp_path / "saved.mp4"
    output.write_bytes(b"previous-output")
    real_run = subprocess.run
    commands = []
    def run(command, **kwargs):
        commands.append(command)
        return real_run(command, **kwargs)
    with mock.patch.object(pipeline.subprocess, "run", side_effect=run):
        with pytest.raises(InvalidMedia):
            pipeline.render_highlight_clip(source_video=str(FIXTURES / "tiny-video.mp4"),
                start_time=210, end_time=268, output_path=output, subtitle_style="none")
    assert output.read_bytes() == b"previous-output"
    assert all("ffprobe" in c[0] for c in commands)


def test_successful_ffmpeg_with_empty_video_never_replaces_final_mp4(tmp_path, monkeypatch):
    from src import pipeline
    output = tmp_path / "saved.mp4"
    output.write_bytes(b"previous-output")
    monkeypatch.setattr(pipeline, "TEMP_DIR", tmp_path)
    real_run = subprocess.run
    def run(command, **kwargs):
        if Path(command[0]).stem == "ffmpeg":
            Path(command[-1]).write_bytes((FIXTURES / "empty-video.mp4").read_bytes())
            return mock.Mock(returncode=0, stderr="")
        return real_run(command, **kwargs)
    with mock.patch.object(pipeline.subprocess, "run", side_effect=run):
        with pytest.raises(InvalidMedia):
            pipeline.render_highlight_clip(source_video=str(FIXTURES / "tiny-video.mp4"),
                start_time=0, end_time=.1, output_path=output, subtitle_style="none")
    assert output.read_bytes() == b"previous-output"
    assert not list(tmp_path.glob("*.rendering.*"))


@pytest.mark.parametrize("changes", [
    {"http_status": 400}, {"http_status": 503}, {"id": "other"}, {"error": "unknown"},
    {"copyright_matches": True}, {"copyright_matches": None}, {"publishing_status": "published"},
    {"publishing_status": "scheduled"}, {"publishing_status": "in_progress"},
    {"video_status": "upload_complete"}, {"video_status": "processing"},
])
def test_uncertain_published_or_scheduled_meta_object_cannot_be_replaced(changes):
    assert not can_replace_failed_video(failed_post(), rejected_seen(**changes))


def test_replacement_preserves_failed_id_and_cms_url_and_cannot_be_created_twice(tmp_path):
    (tmp_path / "repaired.mp4").write_bytes((FIXTURES / "tiny-video.mp4").read_bytes())
    original = failed_post()
    posts = [original]
    replacement, created = prepare_replacement(posts, original, rejected_seen(), tmp_path,
        filename="repaired.mp4", schedule_time=int(time.time()) + 3600)
    assert created and replacement["status"] == "meta_handoff" and original["status"] == "superseded"
    assert original["meta_upload_video_id"] == "9001" and original["meta_post_id"] == "9901_9001"
    assert replacement["article_url"] == original["article_url"]
    assert replacement["first_comment_snapshot"] == original["first_comment_snapshot"]
    assert replacement["first_comment"].count(original["article_url"]) == 1
    assert not replacement.get("meta_upload_video_id") and not replacement.get("outcome_unknown")
    same, created_again = prepare_replacement(posts, original, rejected_seen(), tmp_path,
        filename="repaired.mp4", schedule_time=int(time.time()) + 3600)
    assert not created_again and same["id"] == replacement["id"] and len(posts) == 2


def test_invalid_replacement_does_not_retire_old_meta_id(tmp_path):
    (tmp_path / "broken.mp4").write_bytes((FIXTURES / "empty-video.mp4").read_bytes())
    original = failed_post()
    before = copy.deepcopy(original)
    with pytest.raises(InvalidMedia):
        prepare_replacement([original], original, rejected_seen(), tmp_path,
            filename="broken.mp4", schedule_time=int(time.time()) + 3600)
    assert original == before


def test_worker_keeps_rejected_video_observation_instead_of_reading_finish_post_id(tmp_path, monkeypatch):
    from web import scheduled_publisher as worker
    from src.publisher import first_comment_queue
    from web.posts_store import save_posts_file, load_posts_file
    path = tmp_path / "posts.json"
    post = failed_post()
    post.update(token="fixture", scheduled_time="2026-01-01 00:00:00")
    save_posts_file(path, [post])
    monkeypatch.setattr(worker, "POSTS_FILE", path)
    monkeypatch.setattr(first_comment_queue, "QUEUE_FILE", tmp_path / "comments.json")
    seen = rejected_seen()
    with mock.patch("src.publisher.meta_preflight.preflight_pages", return_value={"ok": True,
            "ready": [{"token": "fixture", "token_id": "original"}]}), \
         mock.patch("src.publisher.page_manager.PageManager.list_pages", return_value=[{"page_id": "9901"}]), \
         mock.patch.object(MetaReelPoster, "check_processing_reel", return_value={"verified": False, "meta_observation": seen}) as read:
        worker.process_scheduled_posts_once(now=datetime(2026, 10, 5, 20))
    read.assert_called_once()
    assert read.call_args.args[0] == "9001"
    assert load_posts_file(path)[0]["meta_observation"] == seen


def test_replace_api_queues_once_without_uploading_or_deleting_meta(tmp_path, monkeypatch):
    from web import app as api
    from src.publisher import first_comment_queue
    from web.posts_store import save_posts_file, load_posts_file
    output = tmp_path / "output"
    output.mkdir()
    (output / "fixed.mp4").write_bytes((FIXTURES / "tiny-video.mp4").read_bytes())
    path = tmp_path / "posts.json"
    save_posts_file(path, [failed_post()])
    monkeypatch.setattr(api, "POSTS_FILE", path)
    monkeypatch.setattr(api, "OUTPUT_DIR", output)
    monkeypatch.setattr(api, "_inspect_post_meta", lambda _: (rejected_seen(), {"page_token": "fixture"}))
    from src.publisher import website_publisher
    monkeypatch.setattr(website_publisher, "get_clip_metadata", lambda _: {"video_title": "Original launch trailer",
        "youtube_url": "https://youtu.be/2GdRyatht4E", "youtube_id": "2GdRyatht4E"})
    monkeypatch.setattr(first_comment_queue, "QUEUE_FILE", tmp_path / "comments.json")
    body = {"confirm_replace_failed_video": True, "video_id": "9001", "filename": "fixed.mp4", "mode": "meta_scheduled", "schedule_time": int(time.time()) + 3600}
    with mock.patch.object(api.reel_poster, "publish_reel") as upload, mock.patch.object(api.reel_poster, "delete_reel") as delete:
        first = api.app.test_client().post("/api/posts/bad/replace-failed-video", json=body)
        second = api.app.test_client().post("/api/posts/bad/replace-failed-video", json=body)
    assert first.status_code == second.status_code == 200, (first.get_json(), second.get_json())
    assert second.get_json()["already_queued"] and len(load_posts_file(path)) == 2
    upload.assert_not_called()
    delete.assert_not_called()


def test_local_invalid_media_requires_verified_repair_and_refuses_existing_meta_id(tmp_path, monkeypatch):
    from web import app as api
    from web.posts_store import save_posts_file, load_posts_file
    path = tmp_path / "posts.json"
    output = tmp_path / "output"
    output.mkdir()
    clip = output / "broken.mp4"
    clip.write_bytes((FIXTURES / "empty-video.mp4").read_bytes())
    save_posts_file(path, [{"id": "local", "status": "failed", "retry_stage": "invalid_media", "media_file": clip.name}])
    monkeypatch.setattr(api, "POSTS_FILE", path)
    monkeypatch.setattr(api, "OUTPUT_DIR", output)
    client = api.app.test_client()
    assert client.post("/api/posts/local/retry-media").status_code == 409
    clip.write_bytes((FIXTURES / "tiny-video.mp4").read_bytes())
    assert client.post("/api/posts/local/retry-media").status_code == 200
    assert load_posts_file(path)[0]["status"] == "scheduled"
    save_posts_file(path, [{"id": "local", "status": "failed", "retry_stage": "invalid_media",
        "media_file": clip.name, "meta_upload_video_id": "9001"}])
    assert client.post("/api/posts/local/retry-media").status_code == 409
