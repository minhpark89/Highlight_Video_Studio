"""Offline regressions from the v1.2.6 CMS headings and recovery screens."""
import copy
import json
import threading
import time
from pathlib import Path
from unittest import mock

import pytest

from src import content_packages as cp, english_text as english, output_pipeline as output
from src.publisher import website_publisher as website
from src.video_recovery_media import (inventory, checked_video, recovery_interval, recovery_source,
    file_digest, verify_recovery_digest)
from web.video_recovery import prepare_replacement
from web.posts_store import load_posts_file, save_posts_file
from tests.test_video_recovery import failed_post, rejected_seen, FIXTURES

HEADINGS = [
    "Yamadonga Telugu Full Movie | Jr Ntr, Priyamani, Mohan Babu, Ss Rajamouli @Sribalajimovies - Full Uncut Breakdown & Scene Analysis",
    "Key Elements That Define Ek Ka Dum", "Understanding Strategic Vulnerabilities", "A Moment Frozen in Time",
]


@pytest.mark.parametrize("heading", HEADINGS)
def test_real_public_english_heading_and_cms_title(heading):
    article = cp.fallback_package("Original recording")["article_html"]
    english.assert_english(article + "<h2>" + heading + "</h2>")
    english.assert_english_title(heading)


@pytest.mark.parametrize("foreign", ["Cette vidéo présente les détails du jeu", "Het begrijpen van strategische kwetsbaarheden",
    "Comprender las vulnerabilidades estratégicas", "この動画の説明", "Toàn bộ nội dung của video này được trình bày bằng tiếng Việt."])
def test_foreign_heading_or_body_still_rejected(foreign):
    article = cp.fallback_package("Original recording")["article_html"]
    for tag in ("h2", "p"):
        with pytest.raises(ValueError):
            english.assert_english(article + f"<{tag}>{foreign}</{tag}>")


def test_heading_exception_never_blesses_a_prose_paragraph():
    assert not english.is_english("Understanding Strategic Vulnerabilities")
    article = cp.fallback_package("Original recording")["article_html"]
    with pytest.raises(ValueError):
        english.assert_english(article + "<p>Understanding Strategic Vulnerabilities</p>")


def test_bundled_lexicon_has_license_and_no_dependency_on_network(monkeypatch):
    data = Path(english.__file__).parent / "data"
    source = json.loads((data / "english_heading_words.source.json").read_text())
    assert "Copyright" in (data / "CMUDICT_LICENSE.txt").read_text()
    assert len(english._heading_lexicon()) > 100000
    assert file_digest(data / "english_heading_words.txt") == "89134aa67bb30f22112eca1314260c9da5b80de5c3532b4a1d7347dfd2f00b1e"
    assert source
    monkeypatch.setattr(english, "_HEADING_LEXICON", frozenset())
    assert not english._english_heading("Moment Frozen Time")
    assert english._english_heading("A Lesson in Cabin Etiquette")


def test_website_retry_revalidates_good_text_without_forcing_llm():
    item = cp.enqueue_content_package(clip_filename="clip.mp4", title="Original recording", create_website_article=True)
    rows = cp.list_packages()
    rows[0].update(status="failed", website_status="failed", article_url="https://cms.test/blog/story",
                   result=cp.fallback_package("Original recording"))
    cp._write(cp.QUEUE_FILE, rows)
    new = cp.retry_package(item["id"], repair_website=True)
    assert new["repair_existing_article"] and not new.get("regenerate_text")


def test_valid_cms_article_is_revalidated_without_rewrite_or_llm(tmp_path, monkeypatch):
    good = cp.fallback_package("Original recording")
    service = mock.Mock()
    service.read_existing_article.return_value = {"title": HEADINGS[0], "description": good["article_html"] + "<h2>" + HEADINGS[2] + "</h2>"}
    monkeypatch.setattr(website, "get_website_config", lambda: ({}, tmp_path / "config.json"))
    monkeypatch.setattr(website, "WebsiteArticleService", lambda _: service)
    monkeypatch.setattr(website, "get_clip_metadata", lambda _: {"youtube_url": "https://youtu.be/2GdRyatht4E"})
    factory = mock.Mock()
    meta = {"result": good}
    url, _ = website.repair_existing_website_article("https://cms.test/blog/story", "clip.mp4", content_factory=factory, asset_metadata=meta)
    assert url == "https://cms.test/blog/story" and meta["website_repair_verified_at"]
    factory.assert_not_called()
    service.update_existing_article.assert_not_called()
    for name in ("verify_article_english", "verify_article_embed", "verify_article_quality"):
        assert getattr(service, name).called


def source_meta(name="clip.mp4"):
    return {"clip_filename": name, "video_title": "Official launch trailer", "youtube_url": "https://youtu.be/2GdRyatht4E",
            "youtube_id": "2GdRyatht4E", "job_id": "job", "clip_index": 3, "clip_start": 300, "clip_end": 355}


@pytest.fixture
def local(tmp_path, monkeypatch):
    from web import app as api
    from src.publisher import first_comment_queue
    directory = tmp_path / "output"
    directory.mkdir()
    path = tmp_path / "posts.json"
    save_posts_file(path, [failed_post()])
    monkeypatch.setattr(api, "POSTS_FILE", path)
    monkeypatch.setattr(api, "OUTPUT_DIR", directory)
    monkeypatch.setattr(cp, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(website, "_runtime_data_root", lambda: tmp_path)
    monkeypatch.setattr(website, "get_clip_metadata", lambda name: source_meta(name))
    monkeypatch.setattr(api, "_inspect_post_meta", lambda _: (rejected_seen(), {"page_token": "fixture"}))
    monkeypatch.setattr(first_comment_queue, "QUEUE_FILE", tmp_path / "comments.json")
    return api, directory, path


def test_inventory_checks_media_and_reports_claims_and_source(local, monkeypatch):
    api, directory, path = local
    for name, fixture in [("good.mp4", "tiny-video.mp4"), ("held.mp4", "tiny-video.mp4"), ("bad.mp4", "empty-video.mp4"), ("unknown.mp4", "tiny-video.mp4")]:
        (directory / name).write_bytes((FIXTURES / fixture).read_bytes())
    monkeypatch.setattr(website, "get_clip_metadata", lambda name: {} if name == "unknown.mp4" else source_meta(name))
    save_posts_file(path, [failed_post(), {"id": "held", "status": "scheduled", "page_id": "other", "media_file": "held.mp4"}])
    result = api.app.test_client().get("/api/posts/bad/recovery-videos").get_json()
    rows = {p["filename"]: p for p in result["candidates"]}
    assert result["total"] == 4 and rows["good.mp4"]["valid"] and rows["good.mp4"]["duration"] > 0
    assert all(not rows[name]["valid"] and rows[name]["reason"] for name in ("held.mp4", "bad.mp4", "unknown.mp4"))


def test_media_cache_expires_and_preview_refuses_escape(local):
    api, directory, _ = local
    clip = directory / "good.mp4"
    clip.write_bytes((FIXTURES / "tiny-video.mp4").read_bytes())
    assert checked_video(directory, clip.name)[1]["duration"] > 0
    client = api.app.test_client()
    assert client.get("/api/posts/bad/recovery-preview?filename=good.mp4").status_code == 200
    assert client.get("/api/posts/bad/recovery-preview?filename=../outside.mp4").status_code == 409
    clip.write_bytes((FIXTURES / "empty-video.mp4").read_bytes())
    with pytest.raises(ValueError):
        checked_video(directory, clip.name)


def test_replacement_has_no_unrelated_website_and_waits_for_verified_content(local):
    api, directory, path = local
    (directory / "new.mp4").write_bytes((FIXTURES / "tiny-video.mp4").read_bytes())
    client = api.app.test_client()
    body = {"confirm_replace_failed_video": True, "video_id": "9001", "filename": "new.mp4", "mode": "app_queue"}
    with mock.patch.object(api.reel_poster, "publish_reel") as publish, mock.patch.object(api.reel_poster, "delete_reel") as delete:
        assert client.post("/api/posts/bad/replace-failed-video", json=body).status_code == 200
        assert client.post("/api/posts/bad/replace-failed-video", json=body).get_json()["already_queued"]
    rows = load_posts_file(path)
    replacement = next(p for p in rows if p["id"] == "bad_replacement")
    assert replacement["status"] == "preparing" and not replacement["article_url"] and not replacement["first_comment_snapshot"]
    assert not replacement.get("content_frozen_at") and replacement["content_package_id"]
    item = cp.get_package(replacement["content_package_id"])
    item.update(status="ready", article_url="https://cms.test/blog/new", website_status="ready", embed_status="ready",
                website_video_status="youtube_embed_verified", result=cp.fallback_package("Official launch trailer", article_url="https://cms.test/blog/new"))
    cp._apply_to_posts(item)
    replacement = next(p for p in load_posts_file(path) if p["id"] == "bad_replacement")
    assert replacement["status"] == "scheduled" and replacement["first_comment_snapshot"].count(item["article_url"]) == 1
    assert replacement["content_frozen_at"]
    publish.assert_not_called()
    delete.assert_not_called()


@pytest.mark.parametrize("bad_state", [{"website_status": "failed"}, {"embed_status": "failed"}, {"website_video_status": "unknown"}])
def test_recovery_never_becomes_due_with_incomplete_content(local, bad_state):
    api, directory, path = local
    post = {"id": "replacement", "status": "preparing", "video_recovery_preparing": True, "publish_mode": "app_queue"}
    save_posts_file(path, [post])
    item = {"id": "package", "post_ids": ["replacement"], "status": "ready", "article_url": "https://cms.test/blog/new",
            "website_status": "ready", "embed_status": "ready", "website_video_status": "youtube_embed_verified",
            "result": cp.fallback_package("Official launch trailer", article_url="https://cms.test/blog/new"), **bad_state}
    cp._apply_to_posts(item)
    assert load_posts_file(path)[0]["status"] == "preparing"


def test_expired_meta_recovery_schedule_exposes_safe_retry(local):
    api, _, path = local
    save_posts_file(path, [{"id": "replacement", "status": "preparing", "video_recovery_preparing": True,
                           "publish_mode": "meta_scheduled", "scheduled_time": "2026-01-01 10:00:00"}])
    cp._apply_to_posts({"id": "package", "post_ids": ["replacement"], "status": "ready", "article_url": "https://cms.test/blog/new",
        "website_status": "ready", "embed_status": "ready", "website_video_status": "youtube_embed_verified",
        "result": cp.fallback_package("Official launch trailer", article_url="https://cms.test/blog/new")})
    from web.post_retry import can_retry_without_upload
    post = load_posts_file(path)[0]
    assert post["status"] == "failed" and can_retry_without_upload(post) and not post.get("outcome_unknown")


def test_same_bytes_under_different_names_cannot_steal_existing_schedule(local):
    api, directory, path = local
    for name in ("held.mp4", "alias.mp4"):
        (directory / name).write_bytes((FIXTURES / "tiny-video.mp4").read_bytes())
    save_posts_file(path, [failed_post(), {"id": "held", "status": "scheduled", "page_id": "other", "media_file": "held.mp4"}])
    response = api.app.test_client().post("/api/posts/bad/replace-failed-video", json={"confirm_replace_failed_video": True,
        "video_id": "9001", "filename": "alias.mp4", "mode": "app_queue"})
    assert response.status_code == 409 and len(load_posts_file(path)) == 2 and load_posts_file(path)[0]["status"] == "processing"


def test_durable_recovery_claim_restores_after_queue_save_interruption(local):
    _, directory, path = local
    (directory / "new.mp4").write_bytes((FIXTURES / "tiny-video.mp4").read_bytes())
    posts = load_posts_file(path)
    replacement, _ = prepare_replacement(posts, posts[0], rejected_seen(), directory, filename="new.mp4",
        mode="app_queue", content_policy="regenerate", source_metadata=source_meta())
    output.reserve_recovery(replacement, posts[1], posts, root=directory.parent)
    assert output.restore_recovery_intents(directory.parent) == 1
    assert output.restore_recovery_intents(directory.parent) == 0
    rows = load_posts_file(path)
    assert len(rows) == 2 and rows[0]["id"] == "bad_replacement" and rows[1]["status"] == "superseded"


@pytest.mark.parametrize("start,end", [(210, 268), (110, 175), (-1, 55), (float("nan"), 55)])
def test_recovery_bounds_are_inside_actual_source(start, end):
    new_start, new_end, adjusted = recovery_interval({"clip_start": start, "clip_end": end, "clip_index": 3}, 129.6)
    assert adjusted and 0 <= new_start < new_end <= 129.6


def test_render_is_local_idempotent_previewable_and_records_exact_source(local):
    api, directory, path = local
    from web import video_recovery_tasks as tasks
    source = directory.parent / "original.mp4"
    source.write_bytes((FIXTURES / "tiny-video.mp4").read_bytes())
    meta = {**source_meta(), "source_video_path": str(source)}
    completed = threading.Event()
    def render(**kwargs):
        assert 0 <= kwargs["start_time"] < kwargs["end_time"] <= checked_video(directory.parent, source.name)[1]["duration"]
        Path(kwargs["output_path"]).write_bytes(source.read_bytes())
        completed.set()
    with mock.patch.object(website, "get_clip_metadata", return_value=meta), mock.patch.object(api.reel_poster, "publish_reel") as publish:
        task = tasks.start_task(directory.parent, failed_post(), render=render)
        assert completed.wait(10)
        for _ in range(100):
            ready = tasks.task_for(directory.parent, "bad")
            if ready["status"] == "ready":
                break
            time.sleep(.02)
        assert ready["status"] == "ready" and ready["interval_adjusted"]
        assert tasks.start_task(directory.parent, failed_post(), render=render)["id"] == task["id"]
        assert api.app.test_client().get("/api/posts/bad/recovery-preview?filename=" + ready["filename"]).status_code == 200
        recorded = recovery_source(directory.parent, ready["filename"])
        assert recorded["youtube_id"] == meta["youtube_id"] and recorded["clip_end"] <= checked_video(directory.parent, source.name)[1]["duration"]
        recovered_path = directory / ready["filename"]
        recovered_path.write_bytes((FIXTURES / "empty-video.mp4").read_bytes())
        with pytest.raises(ValueError):
            recovery_source(directory.parent, ready["filename"])
    assert len(load_posts_file(path)) == 1
    publish.assert_not_called()


def test_recovery_digest_rejects_changed_file(local):
    _, directory, _ = local
    clip = directory / "good.mp4"
    clip.write_bytes((FIXTURES / "tiny-video.mp4").read_bytes())
    post = {"replacement_video_sha256": file_digest(clip)}
    verify_recovery_digest(post, clip)
    clip.write_bytes(b"changed")
    with pytest.raises(ValueError):
        verify_recovery_digest(post, clip)


def test_actual_renderer_creates_a_valid_preview_from_original_source(local, monkeypatch):
    _, directory, _ = local
    from src import pipeline
    from src.media_validation import probe_video
    source = FIXTURES / "tiny-video.mp4"
    target = directory / "_recovery" / "actual-render.mp4"
    target.parent.mkdir()
    monkeypatch.setattr(pipeline, "TEMP_DIR", directory.parent)
    monkeypatch.setenv("HIGHLIGHT_ENCODER", "cpu")
    pipeline.render_highlight_clip(source_video=str(source), start_time=0,
        end_time=probe_video(source)["duration"], output_path=target, subtitle_style="none")
    assert probe_video(target)["duration"] > 0
    assert not list(target.parent.glob("*.rendering.*"))


def test_render_api_requires_fresh_exact_terminal_meta_state(local, monkeypatch):
    api, _, _ = local
    monkeypatch.setattr(api, "_inspect_post_meta", lambda _: (rejected_seen(publishing_status="published"), {"page_token": "fixture"}))
    with mock.patch("web.video_recovery_tasks.start_task") as render:
        response = api.app.test_client().post("/api/posts/bad/render-recovery", json={"confirm_render": True, "video_id": "9001"})
    assert response.status_code == 409
    render.assert_not_called()
