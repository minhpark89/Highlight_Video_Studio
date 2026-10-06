"""Offline regressions for the two reported v1.2.5 screens."""
import json
import time
from pathlib import Path
from unittest import mock

import pytest

from src import content_packages as cp
from src.article_format import word_count
from src.english_text import assert_english, assert_english_package
from src.publisher import website_publisher as publisher
from web.meta_diagnostics import observation
from web.posts_store import load_posts_file, save_posts_file
from web.video_recovery import prepare_replacement


@pytest.mark.parametrize("mode", ["auto", "llm"])
@pytest.mark.parametrize("failure", [RuntimeError("provider unavailable"), ValueError("invalid JSON"), cp.QuotaError("LLM quota HTTP 429")])
def test_llm_failures_return_valid_fallback_in_both_preferred_modes(mode, failure):
    with mock.patch.object(cp, "_llm_package", side_effect=failure), mock.patch.object(cp, "record_quota_failure", return_value={}):
        result = cp.generate_package("Official launch trailer", mode=mode, article_url="https://cms.test/blog/source")
    assert_english_package(result)
    assert result["source"].startswith("no_llm") and result["fallback_reason"]
    assert word_count(result["article_html"]) >= 600
    assert result["first_comment"].count("https://cms.test/blog/source") == 1


def test_open_quota_circuit_uses_fallback_without_provider_request():
    with mock.patch.object(cp, "circuit_status", return_value={"open": True}), mock.patch.object(cp, "_llm_package") as llm:
        result = cp.generate_package("Official trailer", mode="llm")
    assert_english_package(result)
    assert result["source"] == "no_llm_circuit_open"
    llm.assert_not_called()


def test_valid_llm_content_remains_preferred():
    good = {**cp.fallback_package("Official trailer"), "source": "llm", "llm_model": "fixture"}
    with mock.patch.object(cp, "_llm_package", return_value=good):
        result = cp.generate_package("Official trailer", mode="llm")
    assert result["source"] == "llm" and result["llm_model"] == "fixture"


def test_english_heading_is_accepted_while_foreign_paragraph_remains_blocked():
    article = cp.fallback_package("Official video")["article_html"]
    assert_english(article + "<h2>A Lesson in Cabin Etiquette</h2>")
    with pytest.raises(ValueError):
        assert_english(article + "<h2>Cette vidéo présente les détails du jeu</h2>")
    with pytest.raises(ValueError):
        assert_english(article + "<p>Cette vidéo présente les détails de la nouvelle mise à jour.</p>")


def test_bad_normalized_llm_content_uses_fallback_before_cms():
    bad = {**cp.fallback_package("Official trailer"), "source": "llm"}
    bad["article_html"] += "<p>Cette vidéo présente les détails de la nouvelle mise à jour.</p>"
    with mock.patch.object(cp, "_llm_package", return_value=bad):
        result = cp.generate_package("Official trailer", mode="llm")
    assert result["source"] == "no_llm_validation_fallback"
    assert_english_package(result)


@pytest.mark.skipif(not publisher.HAS_CV2, reason="OpenCV unavailable; ffmpeg path checked separately")
def test_four_by_three_original_yields_wide_source_frame(tmp_path):
    import numpy as np
    source = tmp_path / "source.avi"
    output = tmp_path / "source-frame.jpg"
    writer = publisher.cv2.VideoWriter(str(source), publisher.cv2.VideoWriter_fourcc(*"MJPG"), 2, (320, 240))
    assert writer.isOpened()
    for i in range(20):
        writer.write(np.full((240, 320, 3), 40 + i * 5, dtype=np.uint8))
    writer.release()
    result = publisher.select_smart_video_frame(str(source), 0, 5, str(output))
    assert result and publisher._valid_image_file(result, landscape=True)


def test_four_by_three_source_uses_ffmpeg_when_opencv_is_unavailable(tmp_path, monkeypatch):
    import shutil
    import subprocess
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg unavailable")
    source = tmp_path / "original.mp4"
    frame = tmp_path / "frame.jpg"
    subprocess.run([ffmpeg, "-y", "-f", "lavfi", "-i", "color=c=blue:s=320x240:r=2", "-t", "4", str(source)],
        capture_output=True, check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    monkeypatch.setattr(publisher, "HAS_CV2", False)
    monkeypatch.setattr(publisher, "_runtime_data_root", lambda: tmp_path)
    assert publisher.select_smart_video_frame(str(source), 0, 3, str(frame))
    assert publisher._valid_image_file(str(frame), landscape=True)


@pytest.mark.parametrize("image_ok", [True, False])
def test_thumbnail_prefers_image_model_even_when_text_uses_no_llm(tmp_path, monkeypatch, image_ok):
    source = tmp_path / "original.mp4"
    source.write_bytes(b"fixture")
    config = tmp_path / "website.json"
    config.write_text("{}")
    service = mock.Mock()
    service._presign_and_upload.side_effect = lambda session, path: "https://img.test/" + Path(path).name
    monkeypatch.setattr(publisher, "get_website_config", lambda: ({}, config))
    monkeypatch.setattr(publisher, "get_clip_metadata", lambda name: {"source_video_path": str(source), "clip_start": 0, "clip_end": 9})
    monkeypatch.setattr(publisher, "WebsiteArticleService", lambda path: service)
    monkeypatch.setattr(publisher, "_BackendSession", lambda cfg: mock.Mock())
    monkeypatch.setattr(publisher, "get_image_provider_config", lambda: {"model": "image-fixture"})
    monkeypatch.setattr(publisher, "_valid_image_file", lambda *args, **kwargs: True)
    monkeypatch.setattr(publisher, "select_smart_video_frame", lambda *args: args[3])
    with mock.patch.object(publisher, "generate_llm_hook_image", return_value=str(tmp_path / "hero.jpg") if image_ok else "") as image:
        meta = {}
        hero, body = publisher.extract_and_upload_article_assets("clip.mp4", "Official trailer", mode="no_llm", metadata=meta)
    image.assert_called_once()
    assert len(set([hero, *body])) == 3
    assert all("source_frame_" in url for url in body)
    assert meta["image_source"] == ("image_model" if image_ok else "source_frame")


def test_source_transcript_is_present_in_fallback_article_and_summary():
    source = "The source transcript describes a discussion at the airport gate. The speaker asks whether the boarding pass is valid."
    result = cp.generate_package("Airport gate discussion", summary=source, mode="no_llm")
    assert source.split(".")[0] in result["article_html"]
    assert result["source_summary"] == source


def terminal_seen():
    return observation({"id": "9001", "status": {"video_status": "error", "uploading_phase": {"status": "complete"},
        "processing_phase": {"status": "complete"}, "publishing_phase": {"status": "not_started"},
        "copyright_check_status": {"matches_found": False}}}, 200)


def failed_post():
    return {"id": "bad", "status": "processing", "meta_upload_video_id": "9001", "page_id": "9901", "token_id": "original",
        "media_file": "fixed.mp4", "title": "Official launch trailer", "content": "Watch the full original video.",
        "article_url": "https://cms.test/blog/source", "website_status": "ready", "outcome_unknown": True,
        "first_comment_snapshot": "Watch the full original video here: https://cms.test/blog/source"}


def test_confirmed_failed_video_can_be_removed_with_audit_and_without_meta_write(tmp_path, monkeypatch):
    from web import app as api
    from src.publisher import first_comment_queue
    path = tmp_path / "posts.json"
    save_posts_file(path, [{**failed_post(), "token": "fixture-private"}])
    monkeypatch.setattr(api, "POSTS_FILE", path)
    monkeypatch.setattr(first_comment_queue, "QUEUE_FILE", tmp_path / "comments.json")
    monkeypatch.setattr(api, "_inspect_post_meta", lambda p: (terminal_seen(), {"page_token": "fixture-private"}))
    with mock.patch.object(api.reel_poster, "delete_reel") as delete, mock.patch.object(api.reel_poster, "publish_reel") as publish:
        response = api.app.test_client().delete("/api/posts/bad")
    assert response.status_code == 200 and response.get_json()["can_repost"]
    assert not load_posts_file(path)
    audit = tmp_path / "data/meta_failed_removed.json"
    assert json.loads(audit.read_text())[0]["video_id"] == "9001"
    assert "fixture-private" not in audit.read_text() + response.get_data(as_text=True)
    delete.assert_not_called()
    publish.assert_not_called()


@pytest.mark.parametrize("changes", [{"publishing_status": "scheduled"}, {"publishing_status": "published"},
    {"http_status": 400}, {"video_status": "upload_complete"}, {"copyright_matches": True}])
def test_unknown_scheduled_or_identity_restricted_video_cannot_be_deleted(tmp_path, monkeypatch, changes):
    from web import app as api
    path = tmp_path / "posts.json"
    save_posts_file(path, [failed_post()])
    monkeypatch.setattr(api, "POSTS_FILE", path)
    monkeypatch.setattr(api, "_inspect_post_meta", lambda p: ({**terminal_seen(), **changes}, {"page_token": "fixture"}))
    response = api.app.test_client().delete("/api/posts/bad")
    assert response.status_code == 409
    assert load_posts_file(path)[0]["meta_upload_video_id"] == "9001"


def test_app_replacement_keeps_failed_id_and_article_without_requiring_future_meta_time(tmp_path):
    (tmp_path / "fixed.mp4").write_bytes((Path(__file__).parent / "fixtures/tiny-video.mp4").read_bytes())
    original = failed_post()
    posts = [original]
    replacement, created = prepare_replacement(posts, original, terminal_seen(), tmp_path, filename="fixed.mp4", mode="app_queue")
    assert created and replacement["status"] == "scheduled" and replacement["publish_mode"] == "app_queue"
    assert original["status"] == "superseded" and original["meta_upload_video_id"] == "9001"
    assert replacement["article_url"] == original["article_url"] and not replacement.get("meta_upload_video_id")


def test_website_429_sets_delayed_bounded_retry_without_llm_circuit_dependency():
    item = {"clip_filename": "clip.mp4", "create_website_article": True}
    with mock.patch.object(publisher, "publish_clip_to_website_cms", side_effect=RuntimeError("CMS HTTP 429: rate limited")):
        url, state, _ = cp.resolve_article_url(item)
    assert state == "failed" and item["website_retry_scheduled"]
    item["status"] = "retryable"
    assert not cp.package_due(item, now=time.time())
    assert cp.package_due(item, now=item["next_retry_at"] + 1)


def test_retry_package_relinks_post_and_forces_fresh_content():
    item = cp.enqueue_content_package(clip_filename="clip.mp4", title="Official trailer")
    items = cp.list_packages()
    items[0].update(status="failed", website_error="old content failure", result={"source": "llm"})
    cp._write(cp.QUEUE_FILE, items)
    new = cp.retry_package(item["id"], repair_website=True, post_id="post")
    assert new["post_ids"] == ["post"] and new["regenerate_text"] and new["status"] == "queued"
    assert not new["website_error"]


def test_cached_original_transcript_is_used_without_network(tmp_path, monkeypatch):
    monkeypatch.setattr(publisher, "_runtime_data_root", lambda: tmp_path)
    segments = [{"text": "The speaker discusses the airport gate and boarding pass."}]
    excerpt = publisher.source_transcript_excerpt(segments)
    summary = publisher._source_video_summary({"source_transcript_excerpt": excerpt, "youtube_id": "abcdefghijk"}, "Airport gate discussion")
    result = cp.generate_package("Airport gate discussion", summary, mode="no_llm")
    assert excerpt in result["article_html"] and "source transcript passages" in summary
    assert_english_package(result)


@pytest.mark.parametrize("body,valid", [
    ('<a href="https://www.youtube-nocookie.com/embed/abcdefghijk">Video</a>', False),
    ('<iframe src="https://evil.test/embed/abcdefghijk"></iframe>', False),
    ('<iframe src="https://www.youtube-nocookie.com/embed/other-id-12"></iframe>', False),
    ('<iframe src="https://www.youtube-nocookie.com/embed/abcdefghijk"></iframe>', True),
])
def test_website_verifies_real_original_embed_not_a_plain_link(body, valid):
    from core.website_article_service import WebsiteArticleService, WebsiteServiceError
    service = WebsiteArticleService.__new__(WebsiteArticleService)
    service.cfg = mock.Mock(timeout=3)
    with mock.patch("core.website_article_service.requests.get", return_value=mock.Mock(status_code=200, text=body)):
        if valid:
            assert service.verify_article_embed("https://cms.test/blog/source", youtube_id="abcdefghijk")["success"]
        else:
            with pytest.raises(WebsiteServiceError):
                service.verify_article_embed("https://cms.test/blog/source", youtube_id="abcdefghijk")


def test_meta_v24_page_access_cache_refreshes_exact_mapping_and_rejects_failed_discovery(tmp_path, monkeypatch):
    from src.publisher.page_manager import PageManager
    from src.publisher.token_vault import TokenVault
    from src.publisher.meta_preflight import resolve_page_token
    vault, pages = TokenVault(tmp_path), PageManager(tmp_path)
    entry = {"id": "root", "name": "Fixture", "token": "fixture-root", "status": "ACTIVE"}
    vault._save([entry])
    discovery = [{"id": "9901", "name": "Page", "access_token": "fixture-page", "tasks": ["CREATE_CONTENT", "MODERATE"]}]
    clock = [1000]
    monkeypatch.setattr("src.publisher.token_vault.time.monotonic", lambda: clock[0])
    verify = mock.Mock(return_value={"status": "ACTIVE", "pages": discovery})
    monkeypatch.setattr(vault, "verify_token", verify)
    target = {"page_id": "9901", "token_id": "root"}
    assert resolve_page_token(target, vault, pages, refresh=True)["token"] == "fixture-page"
    assert resolve_page_token(target, vault, pages, refresh=True, operation="comment")["ok"]
    assert verify.call_count == 1
    clock[0] += 301
    verify.return_value = {"status": "ERROR", "error": "Fixture discovery unavailable"}
    blocked = resolve_page_token(target, vault, pages, refresh=True)
    assert not blocked["ok"] and blocked["code"] == "page_access_refresh_failed"
    assert verify.call_count == 2
    assert not resolve_page_token(target, vault, pages, refresh=True)["ok"]
    assert verify.call_count == 2


def test_website_quality_counts_distinct_images_inside_article_only():
    from core.website_article_service import WebsiteArticleService, WebsiteServiceError
    service = WebsiteArticleService.__new__(WebsiteArticleService)
    service.cfg = mock.Mock(timeout=3)
    body = '<article><h2>Original video summary</h2>' + '<p>Watch the original video sequence.</p>' * 130
    body += '<img src="https://img.test/one"><img src="https://img.test/one"><h2>Full Uncut Footage</h2></article>'
    body += '<img src="https://img.test/sidebar"><img src="https://img.test/footer">'
    with mock.patch("core.website_article_service.requests.get", return_value=mock.Mock(status_code=200, text=body)):
        with pytest.raises(WebsiteServiceError):
            service.verify_article_quality("https://cms.test/blog/source")
