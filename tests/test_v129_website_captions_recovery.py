import copy
import json
import re
import subprocess
import threading
import time
import wave
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

from core.article_quality import article_quality
from core.text_encoding import repair_mojibake_text, mojibake_marker_score
from core.website_article_service import WebsiteArticleService, WebsiteServiceError
from src import captions, content_packages as cp, pipeline
from src.caption_timing import transcribe_slice
from src.video_recovery_media import reusable_content, file_digest
from tests.test_v127_media_and_cms import local, source_meta
from tests.test_video_recovery import failed_post, rejected_seen, FIXTURES
from web.posts_store import load_posts_file, save_posts_file

URL = "https://cms.test/blog/story"
YOUTUBE_ID = "2GdRyatht4E"


def test_actual_legacy_public_layout_accepts_different_headings_and_keeps_quality_gates():
    body = (FIXTURES / "cms-v129-legacy-heading.html").read_text(encoding="utf-8")
    assert "Original video summary" not in body
    quality = article_quality(body)
    assert quality["word_count"] >= 600 and quality["image_count"] == 3
    for damaged in (re.sub(r"<img\b[^>]*>", "", body), re.sub(r"<iframe\b.*?</iframe>", "", body, flags=re.S),
                    '<p>Short summary.</p><iframe src="https://video.test"></iframe>' + '<img src="1"><img src="2"><img src="3">'):
        with pytest.raises(WebsiteServiceError):
            article_quality(damaged)


def test_public_verification_refuses_redirected_page_even_with_valid_article():
    service = WebsiteArticleService.__new__(WebsiteArticleService)
    service.cfg = SimpleNamespace(timeout=3)
    body = (FIXTURES / "cms-v129-legacy-heading.html").read_text(encoding="utf-8")
    with mock.patch("core.website_article_service.requests.get", return_value=SimpleNamespace(status_code=200, text=body, url="https://cms.test/blog/other")):
        with pytest.raises(WebsiteServiceError, match="chuyển hướng"):
            service.verify_article_quality(URL)


def test_api_repairs_old_errors_for_posts_and_content_studio_without_mutating_identity(tmp_path, monkeypatch):
    from web import app as api
    message = "Bài public thiếu phần tóm tắt hoặc video gốc"
    corrupt = message.encode("utf-8").decode("latin1")
    filename = "Cáº£nh Sát.mp4"
    post = {"id": "error", "status": "preparing", "page_id": "page", "token_id": "token",
            "media_file": filename, "website_error": corrupt, "content_package_error": corrupt}
    path = tmp_path / "posts.json"
    save_posts_file(path, [post])
    before = path.read_bytes()
    monkeypatch.setattr(api, "POSTS_FILE", path)
    item = cp.enqueue_content_package(clip_filename=filename, title="Original recording")
    items = cp.list_packages()
    items[0].update(status="failed", website_error=corrupt, error=corrupt)
    cp._write(cp.QUEUE_FILE, items)
    client = api.app.test_client()
    response = client.get("/api/posts/list?view=review")
    data = response.get_json()["items"][0]
    assert data["website_error"] == message and data["media_file"] == filename
    assert response.content_type == "application/json; charset=utf-8"
    data = client.get("/api/content-studio/queue").get_json()["items"][0]
    assert data["error"] == message and data["clip_filename"] == filename
    assert path.read_bytes() == before and cp.get_package(item["id"])["error"] == corrupt
    assert repair_mojibake_text("Chữ sạch · " + corrupt) == "Chữ sạch · " + message
    normalized_legacy = " ".join(corrupt.split())
    assert repair_mojibake_text(normalized_legacy) == message
    assert mojibake_marker_score(Path("core/website_article_service.py").read_text(encoding="utf-8")) == 0


def test_real_word_times_remain_clip_relative_and_no_pre_cut_words_or_overflow():
    segments = [{"start": 9, "duration": 4, "text": "before exact speech", "words": [
        {"word": "before", "start": 9, "end": 9.7}, {"word": "exact", "start": 10.2, "end": 10.7},
        {"word": "speech", "start": 11.4, "end": 13}]}]
    words = pipeline.transcript_segments_to_words(segments, 10, 2, exact_only=True)
    assert [w["word"] for w in words] == ["exact", "speech"]
    assert words[0]["start"] == pytest.approx(.2) and words[0]["end"] == pytest.approx(.7)
    assert words[1]["end"] == 2
    assert not pipeline.transcript_segments_to_words([{"start": 9, "duration": 4, "text": "no word timestamps"}], 10, 2, exact_only=True)
    coarse = pipeline.transcript_segments_to_words([{"start": 9, "duration": 3, "text": "before clip starts"}], 10, 2)
    assert [w["word"] for w in coarse] == ["clip", "starts"]


def test_json3_retains_real_word_offsets_and_does_not_extend_past_next_cue(tmp_path):
    path = tmp_path / "caption.json3"
    path.write_text(json.dumps({"events": [
        {"tStartMs": 10000, "dDurationMs": 5000, "segs": [{"utf8": "real", "tOffsetMs": 200}, {"utf8": " speech", "tOffsetMs": 1100}]},
        {"tStartMs": 12000, "dDurationMs": 1000, "segs": [{"utf8": "next sentence"}]}]}))
    result = pipeline._parse_ytdlp_json3(path)
    assert result[0]["words"][0]["start"] == 10.2
    assert result[0]["words"][-1]["end"] == 12
    assert not result[1].get("words")


def test_audio_alignment_uses_decoded_pcm_and_reuses_cache_across_font_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "TEMP_DIR", tmp_path)
    source = tmp_path / "source.wav"
    with wave.open(str(source), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\0\0" * 16000)
    word = SimpleNamespace(word="Hello", start=.1, end=.4)
    with mock.patch.object(pipeline, "_transcribe_whisper", return_value=([SimpleNamespace(words=[word])], None)) as transcribe:
        first = transcribe_slice(source, 0, .8, pipeline)
        second = transcribe_slice(source, 0, .8, pipeline)
        assert first == second and transcribe.call_count == 1
        transcribe_slice(source, .1, .7, pipeline)
        assert transcribe.call_count == 2
    assert list((tmp_path / "caption_timing").glob("*.json"))
    assert not list((tmp_path / "caption_timing").glob("*.wav"))


@pytest.mark.parametrize("style", ["viral_anton", "viral_condensed", "viral_vietnam", "karaoke_cyan"])
def test_presets_have_real_font_files_and_bounded_nonoverlapping_events(tmp_path, style):
    path = tmp_path / (style + ".ass")
    words = [{"word": "Cảnh", "start": .005, "end": .4}, {"word": "Sát", "start": .35, "end": .55},
             {"word": "Đẹp", "start": .8, "end": 1.2}, {"word": "{bad\\tag}", "start": 3, "end": 3.2}]
    pipeline.generate_karaoke_ass(words, path, style_name=style, width=1080, height=1080)
    text = path.read_text(encoding="utf-8")
    assert "PlayResY: 1080" in text and captions.STYLES[style]["font"] in text
    assert "bad\\tag" not in text and len(re.findall(r"^Dialogue:", text, re.M)) == 4
    manifest = json.loads((captions.FONTS_DIR / "provenance.json").read_text())
    for item in manifest["fonts"]:
        assert file_digest(captions.FONTS_DIR / item["file"]) == item["sha256"]


def test_actual_ffmpeg_renders_portable_font_and_none_never_reuses_stale_ass(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "TEMP_DIR", tmp_path)
    monkeypatch.setenv("HIGHLIGHT_ENCODER", "cpu")
    source = FIXTURES / "tiny-video.mp4"
    segments = [{"start": 0, "duration": .8, "text": "Cảnh Sát Đẹp", "words": [
        {"word": "Cảnh", "start": .1, "end": .3}, {"word": "Sát", "start": .3, "end": .5}, {"word": "Đẹp", "start": .5, "end": .7}]}]
    with mock.patch.object(pipeline, "get_word_level_transcription") as speech:
        result = pipeline.render_highlight_clip(source_video=str(source), start_time=0, end_time=.8,
            output_path=tmp_path / "font.mp4", subtitle_style="viral_vietnam", all_segments=segments)
    speech.assert_not_called()
    assert result.is_file()
    Path(tmp_path / "plain.ass").write_text("stale caption")
    commands = []
    real = subprocess.run
    def run(command, **kwargs):
        commands.append(command)
        return real(command, **kwargs)
    with mock.patch.object(pipeline.subprocess, "run", side_effect=run):
        pipeline.render_highlight_clip(source_video=str(source), start_time=0, end_time=.3,
            output_path=tmp_path / "plain.mp4", subtitle_style="none")
    assert all("subtitles=" not in str(command) for command in commands)


def test_burned_source_caption_at_bottom_edge_is_hidden_and_cleanup_can_be_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "TEMP_DIR", tmp_path)
    monkeypatch.setenv("HIGHLIGHT_ENCODER", "cpu")
    source = tmp_path / "bottom-caption.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
        "color=c=blue:s=320x568:r=30:d=0.5,drawbox=x=0:y=ih*0.94:w=iw:h=ih*0.04:color=white:t=fill",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source)], check=True,
        capture_output=True, creationflags=pipeline.NO_WINDOW)
    segments = [{"start": 0, "duration": .5, "text": "Hello", "words": [
        {"word": "Hello", "start": .1, "end": .3}]}]
    for cleanup in (True, False):
        monkeypatch.setattr(pipeline, "config", {"video_pipeline": {"source_caption_cleanup": cleanup}})
        rendered = pipeline.render_highlight_clip(source_video=str(source), start_time=0, end_time=.4,
            output_path=tmp_path / f"cleanup-{cleanup}.mp4", subtitle_style="viral_anton", all_segments=segments)
        frame = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", "0.2", "-i", str(rendered),
            "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"],
            check=True, capture_output=True, creationflags=pipeline.NO_WINDOW).stdout
        lower = frame[(1830 * 1080 + 540) * 3:(1830 * 1080 + 540) * 3 + 3]
        upper = frame[(300 * 1080 + 540) * 3:(300 * 1080 + 540) * 3 + 3]
        assert max(lower) < 10 if cleanup else min(lower) > 230
        assert upper[2] > 200 and max(upper[:2]) < 15


def test_archive_unverified_meta_row_is_immediate_durable_and_hidden(local):
    api, _, path = local
    from web.scheduled_publisher import _cycle_lock
    from web.meta_recovery import can_refresh_existing
    original = failed_post()
    original.update(outcome_unknown=True, meta_last_publish_attempt={"state": "unknown"})
    save_posts_file(path, [original])
    _cycle_lock.acquire()
    try:
        with mock.patch.object(api, "_inspect_post_meta") as inspect, mock.patch.object(api.reel_poster, "delete_reel") as remove:
            response = api.app.test_client().delete("/api/posts/bad", json={"archive_local": True})
    finally:
        _cycle_lock.release()
    assert response.status_code == 200 and response.get_json()["archived"]
    archived = load_posts_file(path)[0]
    assert archived["meta_upload_video_id"] == "9001" and archived["local_archived_at"]
    assert archived["status"] == original["status"] and archived["meta_last_publish_attempt"] == original["meta_last_publish_attempt"]
    assert not api.read_posts_snapshot() and not can_refresh_existing(archived)
    assert api.app.test_client().get("/api/posts/list").get_json()["total"] == 0
    assert api.app.test_client().get("/api/posts").get_json() == []
    history = api.app.test_client().get("/api/posts/archived").get_json()
    assert history["total"] == 1 and history["items"][0]["meta_upload_video_id"] == "9001"
    assert api.app.test_client().post("/api/posts/bad/auto-recover", json={}).status_code == 409
    inspect.assert_not_called()
    remove.assert_not_called()


def ready_package(name, sha):
    item = cp.enqueue_content_package(clip_filename=name, title="Official launch trailer", source_sha256=sha,
        video_url=f"https://youtu.be/{YOUTUBE_ID}", create_website_article=True)
    rows = cp.list_packages()
    rows[-1].update(status="ready", article_url=URL, website_status="ready", embed_status="ready",
        website_video_status="youtube_embed_verified", result=cp.fallback_package("Official launch trailer", article_url=URL))
    cp._write(cp.QUEUE_FILE, rows)
    return rows[-1]


def test_reusable_content_rejects_other_source_changed_bytes_and_wrong_comment():
    item = ready_package("stock.mp4", "hash")
    assert reusable_content("stock.mp4", "hash", source_meta("stock.mp4"), [item])["id"] == item["id"]
    assert not reusable_content("stock.mp4", "different", source_meta(), [item])
    for changes in ({"video_url": "https://youtu.be/dQw4w9WgXcQ"}, {"website_status": "failed"},
                    {"result": {**item["result"], "first_comment": "Wrong article https://cms.test/other"}}):
        assert not reusable_content("stock.mp4", "hash", source_meta(), [{**item, **changes}])


def test_one_click_prefers_stock_with_existing_website_and_comment_and_never_renders(local):
    api, directory, path = local
    for name in ("stock.mp4", "new.mp4"):
        (directory / name).write_bytes((FIXTURES / "tiny-video.mp4").read_bytes())
    item = ready_package("stock.mp4", file_digest(directory / "stock.mp4"))
    with mock.patch("web.video_recovery_tasks.start_task") as render, mock.patch.object(api.reel_poster, "publish_reel") as publish:
        response = api.app.test_client().post("/api/posts/bad/auto-recover", json={"mode": "app_queue"})
    assert response.status_code == 200, response.get_json()
    replacement = next(row for row in load_posts_file(path) if row["id"] == "bad_replacement")
    assert replacement["article_url"] == URL and replacement["recovery_reuse_package_id"] == item["id"]
    assert replacement["content_package_id"] == item["id"] and replacement["status"] == "scheduled"
    package = cp.get_package(item["id"])
    assert package["status"] == "ready" and replacement["id"] in package["post_ids"]
    assert not package.get("repair_existing_article") and not package.get("regenerate_text")
    assert api.app.test_client().post("/api/posts/bad/replace-failed-video", json={
        "confirm_replace_failed_video": True, "video_id": "9001", "filename": "stock.mp4", "mode": "app_queue"}).get_json()["already_queued"]
    repeated = api.app.test_client().post("/api/posts/bad/auto-recover", json={})
    assert repeated.status_code == 200 and repeated.get_json()["already_queued"]
    render.assert_not_called()
    publish.assert_not_called()


def test_one_click_checks_beyond_first_inventory_page_before_render(local, monkeypatch):
    api, directory, path = local
    (directory / "stock.mp4").write_bytes((FIXTURES / "tiny-video.mp4").read_bytes())
    pages = []
    def inventory(*args, offset, **kwargs):
        pages.append(offset)
        return {"candidates": [] if offset == 0 else [{"filename": "stock.mp4", "valid": True}], "next_offset": 12 if offset == 0 else None}
    monkeypatch.setattr("src.video_recovery_media.inventory", inventory)
    with mock.patch("web.video_recovery_tasks.start_task") as render:
        assert api.app.test_client().post("/api/posts/bad/auto-recover", json={}).status_code == 200
    assert pages == [0, 12]
    render.assert_not_called()


def test_one_click_prefers_ready_content_on_later_page_over_unprepared_stock(local, monkeypatch):
    api, directory, path = local
    for name in ("new.mp4", "stock.mp4"):
        (directory / name).write_bytes((FIXTURES / "tiny-video.mp4").read_bytes())
    ready_package("stock.mp4", file_digest(directory / "stock.mp4"))
    visited = []
    def inventory(*args, offset, **kwargs):
        visited.append(offset)
        return {"candidates": [{"filename": "new.mp4", "valid": True}] if offset == 0 else
                [{"filename": "stock.mp4", "valid": True, "ready_content": True}],
                "next_offset": 12 if offset == 0 else None}
    monkeypatch.setattr("src.video_recovery_media.inventory", inventory)
    with mock.patch("web.video_recovery_tasks.start_task") as render:
        response = api.app.test_client().post("/api/posts/bad/auto-recover", json={})
    assert response.status_code == 200, response.get_json()
    assert visited == [0, 12]
    replacement = next(row for row in load_posts_file(path) if row["id"] == "bad_replacement")
    assert replacement["media_file"] == "stock.mp4" and replacement["recovery_reuse_package_id"]
    render.assert_not_called()


def test_one_click_accepts_timezone_aware_app_schedule(local):
    api, directory, path = local
    (directory / "stock.mp4").write_bytes((FIXTURES / "tiny-video.mp4").read_bytes())
    schedule = (datetime.now().astimezone() + timedelta(hours=2)).isoformat()
    response = api.app.test_client().post("/api/posts/bad/auto-recover",
        json={"mode": "app_queue", "schedule_time": schedule})
    assert response.status_code == 200, response.get_json()
    replacement = next(row for row in load_posts_file(path) if row["id"] == "bad_replacement")
    assert datetime.fromisoformat(replacement["scheduled_time"]).timestamp() == pytest.approx(
        datetime.fromisoformat(schedule).timestamp(), abs=1)


def test_local_archive_returns_while_comment_worker_holds_queue_lock(local):
    api, _, path = local
    from src.publisher import first_comment_queue as comments
    from web.posts_store import _LOCK as posts_lock
    held = threading.Event()
    read_posts = threading.Event()
    def active_comment_worker():
        with comments._LOCK:
            held.set()
            assert read_posts.wait(3)
            with posts_lock:
                return load_posts_file(path)[0]
    with ThreadPoolExecutor(max_workers=2) as pool:
        worker = pool.submit(active_comment_worker)
        assert held.wait(3)
        try:
            response = pool.submit(lambda: api.app.test_client().delete(
                "/api/posts/bad", json={"archive_local": True})).result(timeout=3)
            assert response.status_code == 200 and response.get_json()["archived"]
        finally:
            read_posts.set()
        assert worker.result(timeout=3)["local_archived_at"]
    comments.enqueue_first_comment("9001", "fixture", "Original video", 1, post_id="bad")
    poster = mock.Mock()
    comments.process_due_first_comments(poster, now=2, prepare=lambda _: {"ready": False, "cancelled": True})
    assert comments._load_unlocked()[0]["status"] == "cancelled"
    poster.post_first_comment.assert_not_called()


def test_one_click_no_stock_persists_render_intent_with_requested_mode(local):
    api, _, _ = local
    schedule = (datetime.now() + timedelta(hours=2)).isoformat()
    with mock.patch("web.video_recovery_tasks.start_task", return_value={"status": "queued"}) as render:
        response = api.app.test_client().post("/api/posts/bad/auto-recover", json={"mode": "meta_scheduled", "schedule_time": schedule})
    assert response.status_code == 202 and response.get_json()["render_started"]
    assert render.call_args.kwargs["auto_action"] == {"mode": "meta_scheduled", "schedule_time": schedule}
    assert api.app.test_client().post("/api/posts/bad/auto-recover", json={"mode": "meta_scheduled"}).status_code == 409


def test_render_intent_automatically_creates_replacement_and_is_restart_idempotent(local, monkeypatch):
    api, directory, path = local
    from web import video_recovery_tasks as tasks
    source = directory.parent / "original.mp4"
    source.write_bytes((FIXTURES / "tiny-video.mp4").read_bytes())
    meta = {**source_meta(), "source_video_path": str(source)}
    monkeypatch.setattr("src.publisher.website_publisher.get_clip_metadata", lambda _: dict(meta))
    def render(**kwargs):
        Path(kwargs["output_path"]).write_bytes(source.read_bytes())
    task = tasks.start_task(directory.parent, failed_post(), render=render, auto_action={"mode": "app_queue", "schedule_time": None})
    for _ in range(200):
        ready = tasks.task_for(directory.parent, "bad")
        if ready.get("replacement_post_id") or ready.get("status") == "error":
            break
        time.sleep(.02)
    assert ready.get("replacement_post_id") == "bad_replacement", ready
    assert not ready["auto_recovery_pending"]
    tasks.complete_auto_recovery(directory.parent, "bad")
    assert len(load_posts_file(path)) == 2


def test_persisted_render_intent_waits_for_long_busy_worker_and_runs_without_request(local, monkeypatch):
    api, directory, path = local
    from web import video_recovery_tasks as tasks
    (directory / "stock.mp4").write_bytes((FIXTURES / "tiny-video.mp4").read_bytes())
    tasks.write_json(tasks._state_file(directory.parent), {"bad": {
        "status": "ready", "filename": "stock.mp4", "sha256": file_digest(directory / "stock.mp4"),
        "video_id": "9001", "auto_action": {"mode": "app_queue", "schedule_time": None},
        "auto_recovery_pending": True}})
    attempts = []
    replace = api.api_replace_failed_video
    def initially_busy(post_id, _body=None):
        from flask import has_request_context, jsonify
        assert not has_request_context()
        attempts.append(_body)
        if len(attempts) <= 25:
            return jsonify({"success": False, "busy": True}), 409
        return replace(post_id, _body=_body)
    monkeypatch.setattr(api, "api_replace_failed_video", initially_busy)
    monkeypatch.setattr(tasks.time, "sleep", lambda _: None)
    tasks.complete_auto_recovery(directory.parent, "bad")
    ready = tasks.task_for(directory.parent, "bad")
    assert len(attempts) == 26 and ready["replacement_post_id"] == "bad_replacement"
    assert not ready["auto_recovery_pending"]
    tasks.complete_auto_recovery(directory.parent, "bad")
    assert len(attempts) == 26 and len(load_posts_file(path)) == 2
